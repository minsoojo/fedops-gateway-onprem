import os
import time
import socket
from typing import Dict, Tuple, Optional, Iterable, List, Any, Union

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from kubernetes import client, config
from kubernetes.client import ApiException

# =============================
# 설정
# =============================
NAMESPACE = os.getenv("POD_NAMESPACE", "fedops")
SERVICE_NAME_FMT = os.getenv("SERVICE_NAME_FMT", "fl-server-service-{taskid}")
CACHE_TTL_SEC = int(os.getenv("SERVICE_CACHE_TTL", "20"))

HTTP_TIMEOUT = float(os.getenv("UPSTREAM_TIMEOUT", "8.0"))

# Resolver 모드: 외부에서 접속 가능한 주소를 어떻게 만들 것인가
# - loadbalancer: Service.type=LoadBalancer의 외부 IP/Hostname(+포트) 반환
# - nodeport:     Service.type=NodePort면 Gateway 노드 IP + nodePort 반환 (GATEWAY_PUBLIC_IP 필요)
# - clusterip:    ClusterIP:port 그대로 반환(클라이언트가 클러스터 내부에서 접근 가능할 때만 유효)
RESOLVE_PREFERENCE = os.getenv("RESOLVE_PREFERENCE", "loadbalancer,nodeport,clusterip").split(",")

# NodePort 모드일 때 사용할 퍼블릭 IP(게이트웨이/노드의 공인 IP)
GATEWAY_PUBLIC_IP = os.getenv("GATEWAY_PUBLIC_IP", "")

# 디폴트로 선택할 포트(없을 때)
DEFAULT_PORT = int(os.getenv("DEFAULT_UPSTREAM_PORT", "8080"))

# =============================
# 전역 리소스
# =============================
app = FastAPI(title="fedops resolver gateway", version="1.0")
_http = httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=False)
_cache: Dict[str, Tuple[float, str, int]] = {}  # taskid -> (expire_at, host, port)
_k8s_ready = False


def _load_k8s():
    global _k8s_ready
    if _k8s_ready:
        return
    try:
        # in-cluster
        config.load_incluster_config()
        _k8s_ready = True
    except Exception:
        # local dev
        config.load_kube_config()
        _k8s_ready = True


def _service_dns_name(taskid: str) -> str:
    return f"{SERVICE_NAME_FMT.format(taskid=taskid)}.{NAMESPACE}.svc.cluster.local"


def _pick_service_port(svc: client.V1Service) -> int:
    ports = svc.spec.ports or []
    if not ports:
        return DEFAULT_PORT
    # 이름이 'grpc'/'http2'/'http'인 포트를 우선
    priority = ("grpc", "http2", "http")
    for key in priority:
        for p in ports:
            name = (p.name or "").lower()
            if key == name and (p.protocol or "TCP") == "TCP":
                return int(p.port)
    # 첫 번째 TCP 포트
    for p in ports:
        if (p.protocol or "TCP") == "TCP":
            return int(p.port)
    return DEFAULT_PORT


def _get_from_cache(taskid: str) -> Optional[Tuple[str, int]]:
    ent = _cache.get(taskid)
    if not ent:
        return None
    exp, host, port = ent
    if exp < time.time():
        _cache.pop(taskid, None)
        return None
    return host, port


def _put_cache(taskid: str, host: str, port: int):
    _cache[taskid] = (time.time() + CACHE_TTL_SEC, host, port)


def _resolve_via_dns(taskid: str) -> Optional[str]:
    # headless 서비스일 경우 파드 IP 여러 개가 나올 수 있음 → 하나 선택
    host = _service_dns_name(taskid)
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        addrs = {info[4][0] for info in infos if info[4]}
        return sorted(addrs)[0] if addrs else None
    except Exception:
        return None


def _best_external_address_for_service(
    svc: client.V1Service, taskid: str
) -> Optional[Tuple[str, int]]:
    """
    Service 타입과 설정에 따라 클라이언트가 실제로 접속할 (host, port)를 만든다.
    우선순위는 RESOLVE_PREFERENCE에 따름.
    """
    stype = (svc.spec.type or "ClusterIP").upper()
    p = _pick_service_port(svc)

    # 후보 생성
    candidates: List[Tuple[str, int, str]] = []  # (host, port, kind)

    # 1) LoadBalancer
    if stype == "LOADBALANCER":
        ing = (svc.status.load_balancer.ingress or [])  # type: ignore
        for item in ing:
            if getattr(item, "ip", None):
                candidates.append((item.ip, p, "loadbalancer"))
            elif getattr(item, "hostname", None):
                candidates.append((item.hostname, p, "loadbalancer"))

    # 2) NodePort
    # Service가 NodePort일 때, nodePort를 사용해 Gateway public IP로 연결
    if stype in ("NODEPORT", "LOADBALANCER"):
        # ports의 node_port가 설정되어 있으면 그걸 사용
        node_ports = [int(x.node_port) for x in (svc.spec.ports or []) if x.node_port]
        if node_ports and GATEWAY_PUBLIC_IP:
            # 단순화: 첫 nodePort 사용
            candidates.append((GATEWAY_PUBLIC_IP, node_ports[0], "nodeport"))

    # 3) ClusterIP
    cluster_ip = getattr(svc.spec, "cluster_ip", None)
    if cluster_ip and cluster_ip not in ("None", None):
        # 클러스터 내부에서만 접근 가능
        candidates.append((cluster_ip, p, "clusterip"))

    # 4) Headless → DNS 파드 IP
    if not cluster_ip or cluster_ip == "None":
        ip = _resolve_via_dns(taskid)
        if ip:
            candidates.append((ip, p, "headless-dns"))

    # 우선순위 필터링
    for pref in RESOLVE_PREFERENCE:
        for host, port, kind in candidates:
            if kind.lower() == pref.lower():
                return host, port

    # 그래도 없으면 첫 후보
    return (candidates[0][0], candidates[0][1]) if candidates else None


def _lookup_service_hostport(taskid: str) -> Tuple[str, int]:
    """
    캐시 → K8s API → DNS 폴백으로 (host, port) 결정
    """
    cached = _get_from_cache(taskid)
    if cached:
        return cached

    name = SERVICE_NAME_FMT.format(taskid=taskid)
    _load_k8s()
    v1 = client.CoreV1Api()

    # K8s API 조회
    svc: Optional[client.V1Service] = None
    try:
        svc = v1.read_namespaced_service(name=name, namespace=NAMESPACE)
    except ApiException as e:
        if e.status not in (403, 404):
            # 다른 오류라도 계속 시도
            pass
    except Exception:
        pass

    if svc:
        best = _best_external_address_for_service(svc, taskid)
        if best:
            host, port = best
            _put_cache(taskid, host, port)
            return host, port

    # API 실패 또는 모드에 따른 폴백: DNS(ClusterIP/headless)
    ip = _resolve_via_dns(taskid)
    if ip:
        port = DEFAULT_PORT
        _put_cache(taskid, ip, port)
        return ip, port

    raise RuntimeError(f"service host/port resolve failed for taskid={taskid}")


def _fmt_hostport(host: str, port: int) -> str:
    # IPv6 지원
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return f"[{host}]:{port}"
    except OSError:
        return f"{host}:{port}"


# =============================
# 라우팅
# =============================

@app.get("/healthz")
def healthz():
    return PlainTextResponse("ok")


@app.get("/resolve/{taskid}")
def resolve(taskid: str):
    """
    Flower server_address로 그대로 넣을 HOST:PORT를 반환한다.
    """
    try:
        host, port = _lookup_service_hostport(taskid)
        return JSONResponse({"address": _fmt_hostport(host, port)})
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# 디버그: 네임스페이스 내 Service 목록 보기
def _list_services(namespace: str = NAMESPACE) -> List[Dict[str, Any]]:
    _load_k8s()
    v1 = client.CoreV1Api()
    try:
        services = v1.list_namespaced_service(namespace=namespace)
    except ApiException as e:
        raise HTTPException(
            status_code=e.status or 500,
            detail={
                "message": "failed to list services",
                "namespace": namespace,
                "reason": e.reason,
                "status": e.status,
                "body": e.body,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": str(e)})

    results: List[Dict[str, Any]] = []
    for svc in services.items:
        ports = []
        for p in (svc.spec.ports or []):
            ports.append(
                {
                    "name": p.name,
                    "port": int(p.port),
                    "protocol": p.protocol or "TCP",
                    "targetPort": p.target_port,
                    "nodePort": int(p.node_port) if p.node_port else None,
                }
            )
        results.append(
            {
                "name": svc.metadata.name,
                "type": svc.spec.type,
                "clusterIP": getattr(svc.spec, "cluster_ip", None),
                "ports": ports,
                "lbIngress": [
                    getattr(x, "ip", None) or getattr(x, "hostname", None)
                    for x in (getattr(svc.status.load_balancer, "ingress", []) or [])
                ],
            }
        )
    return results


@app.get("/all")
def get_all_services(namespace: str = NAMESPACE):
    data = _list_services(namespace=namespace)
    payload = {"namespace": namespace, "total": len(data), "services": data}
    return JSONResponse(payload)


# uvicorn 실행 예:
#   python -m uvicorn fedops_gateway:app --host 0.0.0.0 --port 8086
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fedops_gateway:app", host="0.0.0.0", port=8086, reload=True)
