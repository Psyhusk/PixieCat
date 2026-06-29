#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║   modules/pix_telemetry.py                                          ║
║   Motor de Telemetria & Enriquecimento de Metadados Pix             ║
║                                                                      ║
║   Técnicas utilizadas:                                               ║
║   · asyncio + ThreadPoolExecutor — I/O paralelo sem bloqueio        ║
║   · concurrent.futures — pool de threads gerenciado                 ║
║   · dataclasses — tipagem estruturada dos resultados                ║
║   · contextvars — propagação de contexto entre corrotinas           ║
║   · socket fingerprinting — resolução DNS reversa e TCP probe       ║
║   · HTTP telemetry — headers, TLS, latência, redirecionamentos      ║
║   · Triangulação CEP — 3 fontes independentes com votação           ║
║   · Jitter timing — detecção de honeypots por latência              ║
║                                                                      ║
║   Created by psyhusk                                                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import concurrent.futures
import contextvars
import dataclasses
import datetime
import json
import logging
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, Callable, Optional

log = logging.getLogger("pixiecat.telemetry")
log.setLevel(logging.DEBUG)

_session_id:  contextvars.ContextVar[str]   = contextvars.ContextVar("session_id",  default="?")
_analysis_ts: contextvars.ContextVar[float] = contextvars.ContextVar("analysis_ts", default=0.0)

_TIMEOUT    = 6
_MAX_WORKERS= 8

_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Connection":      "keep-alive",
    "DNT":             "1",
}

_REGIOES = {
    "AC":"Norte","AM":"Norte","AP":"Norte","PA":"Norte","RO":"Norte","RR":"Norte","TO":"Norte",
    "AL":"Nordeste","BA":"Nordeste","CE":"Nordeste","MA":"Nordeste","PB":"Nordeste",
    "PE":"Nordeste","PI":"Nordeste","RN":"Nordeste","SE":"Nordeste",
    "DF":"Centro-Oeste","GO":"Centro-Oeste","MS":"Centro-Oeste","MT":"Centro-Oeste",
    "ES":"Sudeste","MG":"Sudeste","RJ":"Sudeste","SP":"Sudeste",
    "PR":"Sul","RS":"Sul","SC":"Sul",
}

_DDD_TO_CEP = {
    "11":"01310100","12":"12210000","13":"11010020","14":"17010000","15":"18010000",
    "16":"14010000","17":"15010000","18":"19010000","19":"13010000","21":"20040020",
    "22":"27910000","24":"24020005","27":"29010010","28":"29300000","31":"30110000",
    "32":"36010001","33":"35010000","34":"38400000","35":"37500000","37":"35500000",
    "38":"39400000","41":"80010000","42":"84010000","43":"86010000","44":"87013000",
    "45":"85810000","46":"85500000","47":"89010000","48":"88010000","49":"89700000",
    "51":"90010000","53":"96010000","54":"95010000","55":"97010000","61":"70040010",
    "62":"74010000","63":"77800000","64":"75800000","65":"78010000","66":"78700000",
    "67":"79002000","68":"69900000","69":"76800000","71":"40010000","73":"45654000",
    "74":"48900000","75":"44001000","77":"47800000","79":"49010000","81":"50010000",
    "82":"57020000","83":"58010000","84":"59010000","85":"60010000","86":"64000000",
    "87":"56300000","88":"62010000","89":"63900000","91":"66010000","92":"69010000",
    "93":"68005000","94":"68400000","95":"69300000","96":"68900000","97":"69100000",
    "98":"65010000","99":"65900000",
}

_PSP_DB = {
    "00000000": {"nome":"Banco do Brasil",        "tipo":"BANCO",       "cidade":"Brasília",      "estado":"DF"},
    "00360305": {"nome":"Caixa Econômica Federal","tipo":"BANCO",       "cidade":"Brasília",      "estado":"DF"},
    "03656248": {"nome":"Nu Pagamentos (Nubank)", "tipo":"FINTECH",     "cidade":"São Paulo",     "estado":"SP"},
    "04902979": {"nome":"Banco Inter",            "tipo":"BANCO",       "cidade":"Belo Horizonte","estado":"MG"},
    "07679404": {"nome":"Banco Itaú Unibanco",    "tipo":"BANCO",       "cidade":"São Paulo",     "estado":"SP"},
    "09089356": {"nome":"Banco Original",         "tipo":"BANCO",       "cidade":"São Paulo",     "estado":"SP"},
    "09526594": {"nome":"C6 Bank",                "tipo":"FINTECH",     "cidade":"São Paulo",     "estado":"SP"},
    "10664513": {"nome":"Mercado Pago",           "tipo":"FINTECH",     "cidade":"São Paulo",     "estado":"SP"},
    "13140088": {"nome":"Banco Bradesco",         "tipo":"BANCO",       "cidade":"Osasco",        "estado":"SP"},
    "14388334": {"nome":"Banco Santander (BR)",   "tipo":"BANCO",       "cidade":"São Paulo",     "estado":"SP"},
    "20018183": {"nome":"Banco Central do Brasil","tipo":"BACEN",       "cidade":"Brasília",      "estado":"DF"},
    "92702067": {"nome":"Banco Sicredi",          "tipo":"COOPERATIVA", "cidade":"Porto Alegre",  "estado":"RS"},
}


@dataclasses.dataclass
class CepResult:
    cep:         str   = ""
    logradouro:  str   = ""
    bairro:      str   = ""
    cidade:      str   = ""
    estado:      str   = ""
    regiao:      str   = ""
    ddd:         str   = ""
    ibge:        str   = ""
    fonte:       str   = ""
    confianca:   int   = 0
    latencia_ms: float = 0.0


@dataclasses.dataclass
class DnsResult:
    hostname:    str       = ""
    ips:         list[str] = dataclasses.field(default_factory=list)
    rdns:        list[str] = dataclasses.field(default_factory=list)
    latencia_ms: float     = 0.0


@dataclasses.dataclass
class HttpProbe:
    url:             str       = ""
    status:          int       = 0
    server:          str       = ""
    content_type:    str       = ""
    x_powered_by:    str       = ""
    tls_version:     str       = ""
    tls_cipher:      str       = ""
    tls_issuer:      str       = ""
    tls_expiry:      str       = ""
    redirects:       list[str] = dataclasses.field(default_factory=list)
    latencia_ms:     float     = 0.0
    suspeito:        bool      = False
    motivo_suspeito: str       = ""


@dataclasses.dataclass
class TelemetryReport:
    session_id:       str                  = ""
    timestamp:        str                  = ""
    duracao_total_ms: float                = 0.0
    cep_payload:      str                  = ""
    cep_triangulado:  Optional[CepResult]  = None
    cep_fontes:       list[CepResult]      = dataclasses.field(default_factory=list)
    cep_consenso:     bool                 = False
    dns:              Optional[DnsResult]  = None
    http_probe:       Optional[HttpProbe]  = None
    psp:              dict                 = dataclasses.field(default_factory=dict)
    geo_ip:           dict                 = dataclasses.field(default_factory=dict)
    anomalias:        list[str]            = dataclasses.field(default_factory=list)
    score_delta:      int                  = 0
    eventos:          list[str]            = dataclasses.field(default_factory=list)


class PixTelemetry:
    """
    Motor de telemetria paralela para enriquecimento de metadados Pix.
    Usa ThreadPoolExecutor com contextvars para rastreio de sessão.
    """

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self._cb       = callback or (lambda m: None)
        self._lock     = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=_MAX_WORKERS,
            thread_name_prefix="pixiecat_tel",
        )

    # ── Entrypoint ────────────────────────────────────────────────────

    def enrich(self, meta: dict, decoded: dict) -> TelemetryReport:
        import uuid
        sid = uuid.uuid4().hex[:12]
        _session_id.set(sid)
        _analysis_ts.set(time.monotonic())

        report            = TelemetryReport()
        report.session_id = sid
        report.timestamp  = datetime.datetime.now().isoformat()
        t0                = time.monotonic()

        self._emit(f"[TEL] Sessão {sid} — telemetria iniciada")

        cep   = meta.get("cep",   "").strip()
        chave = meta.get("chave", "").strip()
        url   = meta.get("url",   "").strip()
        ispb  = meta.get("ispb",  "").strip()
        report.cep_payload = cep

        # ── Submissão paralela ────────────────────────────────────────
        futures: dict[str, concurrent.futures.Future] = {}

        futures["cep_viacep"]   = self._executor.submit(self._cep_viacep,   cep, chave)
        futures["cep_opencep"]  = self._executor.submit(self._cep_opencep,  cep)
        futures["cep_brasilapi"]= self._executor.submit(self._cep_brasilapi, cep)

        if url:
            futures["dns"]       = self._executor.submit(self._dns_probe,  url)
            futures["http"]      = self._executor.submit(self._http_probe, url)
            futures["geo"]       = self._executor.submit(self._geo_ip,     url)

        if ispb:
            futures["psp"]       = self._executor.submit(self._psp_lookup, ispb)

        concurrent.futures.wait(futures.values(), timeout=_TIMEOUT * 2)

        # ── Coleta ───────────────────────────────────────────────────
        cep_results: list[CepResult] = []
        for k in ("cep_viacep", "cep_opencep", "cep_brasilapi"):
            r = self._safe(futures.get(k), k)
            if r and r.cep:
                cep_results.append(r)

        report.cep_fontes      = cep_results
        report.cep_triangulado = self._triangulate(cep_results)
        report.cep_consenso    = len(cep_results) >= 2

        report.dns       = self._safe(futures.get("dns"),  "dns")
        report.http_probe= self._safe(futures.get("http"), "http")
        report.geo_ip    = self._safe(futures.get("geo"),  "geo") or {}
        report.psp       = self._safe(futures.get("psp"),  "psp") or {}

        self._detect_anomalies(report, meta)

        report.duracao_total_ms = (time.monotonic() - t0) * 1000
        self._emit(f"[TEL] Concluído em {report.duracao_total_ms:.0f}ms | "
                   f"anomalias={len(report.anomalias)} delta={report.score_delta}")
        return report

    # ── CEP — ViaCEP ─────────────────────────────────────────────────

    def _cep_viacep(self, cep: str, chave: str) -> Optional[CepResult]:
        target = self._resolve_cep(cep, chave)
        if not target:
            return None
        t0 = time.monotonic()
        try:
            url = f"https://viacep.com.br/ws/{target}/json/"
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=_HEADERS),
                context=ssl.create_default_context(),
                timeout=_TIMEOUT,
            ) as r:
                d = json.loads(r.read())
            if d.get("erro"):
                return None
            ms = (time.monotonic()-t0)*1000
            uf = d.get("uf","")
            self._emit(f"[TEL] ViaCEP → {d.get('localidade')}/{uf} ({ms:.0f}ms)")
            return CepResult(
                cep=re.sub(r"\D","",d.get("cep","")), logradouro=d.get("logradouro",""),
                bairro=d.get("bairro",""), cidade=d.get("localidade",""),
                estado=uf, regiao=_REGIOES.get(uf,""), ddd=d.get("ddd",""),
                ibge=d.get("ibge",""), fonte="ViaCEP", confianca=95, latencia_ms=ms,
            )
        except Exception as e:
            self._emit(f"[TEL] ViaCEP: {type(e).__name__}")
            return None

    # ── CEP — OpenCEP ─────────────────────────────────────────────────

    def _cep_opencep(self, cep: str) -> Optional[CepResult]:
        c = re.sub(r"\D","",cep)
        if len(c) != 8:
            return None
        t0 = time.monotonic()
        try:
            url = f"https://opencep.com/v1/{c}"
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=_HEADERS),
                context=ssl.create_default_context(),
                timeout=_TIMEOUT,
            ) as r:
                d = json.loads(r.read())
            if not d.get("cep"):
                return None
            ms = (time.monotonic()-t0)*1000
            uf = d.get("uf","")
            self._emit(f"[TEL] OpenCEP → {d.get('localidade')}/{uf} ({ms:.0f}ms)")
            return CepResult(
                cep=re.sub(r"\D","",d.get("cep","")), logradouro=d.get("logradouro",""),
                bairro=d.get("bairro",""), cidade=d.get("localidade",""),
                estado=uf, regiao=_REGIOES.get(uf,""), ddd=d.get("ddd",""),
                ibge=d.get("ibge",""), fonte="OpenCEP", confianca=88, latencia_ms=ms,
            )
        except Exception as e:
            self._emit(f"[TEL] OpenCEP: {type(e).__name__}")
            return None

    # ── CEP — BrasilAPI ───────────────────────────────────────────────

    def _cep_brasilapi(self, cep: str) -> Optional[CepResult]:
        c = re.sub(r"\D","",cep)
        if len(c) != 8:
            return None
        t0 = time.monotonic()
        try:
            url = f"https://brasilapi.com.br/api/cep/v2/{c}"
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=_HEADERS),
                context=ssl.create_default_context(),
                timeout=_TIMEOUT,
            ) as r:
                d = json.loads(r.read())
            ms = (time.monotonic()-t0)*1000
            uf = d.get("state","")
            self._emit(f"[TEL] BrasilAPI → {d.get('city')}/{uf} ({ms:.0f}ms)")
            return CepResult(
                cep=re.sub(r"\D","",d.get("cep","")), logradouro=d.get("street",""),
                bairro=d.get("neighborhood",""), cidade=d.get("city",""),
                estado=uf, regiao=_REGIOES.get(uf,""),
                fonte="BrasilAPI", confianca=90, latencia_ms=ms,
            )
        except Exception as e:
            self._emit(f"[TEL] BrasilAPI: {type(e).__name__}")
            return None

    # ── Triangulação ──────────────────────────────────────────────────

    def _triangulate(self, results: list[CepResult]) -> Optional[CepResult]:
        if not results:
            return None
        if len(results) == 1:
            return results[0]
        cidades = Counter(r.cidade.lower().strip() for r in results if r.cidade)
        cidade_win, votos = cidades.most_common(1)[0]
        candidatos = sorted(
            [r for r in results if r.cidade.lower().strip() == cidade_win],
            key=lambda r: r.confianca, reverse=True,
        )
        best = candidatos[0]
        for r in candidatos[1:]:
            if not best.logradouro and r.logradouro: best.logradouro = r.logradouro
            if not best.ddd        and r.ddd:        best.ddd        = r.ddd
            if not best.ibge       and r.ibge:       best.ibge       = r.ibge
        self._emit(f"[TEL] Triangulação: {best.cidade}/{best.estado} — {votos}/{len(results)} fontes")
        return best

    # ── CEP por chave ─────────────────────────────────────────────────

    def _resolve_cep(self, cep: str, chave: str) -> str:
        c = re.sub(r"\D","",cep or "")
        if len(c) == 8:
            return c
        if chave:
            m = re.match(r"^\+?55?(\d{2})", chave)
            if m:
                ddd = m.group(1)
                got = _DDD_TO_CEP.get(ddd,"")
                if got:
                    self._emit(f"[TEL] CEP inferido por DDD {ddd} → {got}")
                    return got
        return ""

    # ── DNS probe ─────────────────────────────────────────────────────

    def _dns_probe(self, url: str) -> Optional[DnsResult]:
        t0 = time.monotonic()
        try:
            host = urllib.parse.urlparse(url).hostname or ""
            if not host:
                return None
            result = DnsResult(hostname=host)
            try:
                result.ips = list({i[4][0] for i in socket.getaddrinfo(host, None)})
                self._emit(f"[TEL] DNS: {host} → {result.ips}")
            except socket.gaierror as e:
                self._emit(f"[TEL] DNS falhou: {e}")
            for ip in result.ips[:2]:
                try:
                    result.rdns.append(socket.gethostbyaddr(ip)[0])
                except Exception:
                    pass
            result.latencia_ms = (time.monotonic()-t0)*1000
            return result
        except Exception as e:
            self._emit(f"[TEL] DNS: {type(e).__name__}")
            return None

    # ── HTTP probe ────────────────────────────────────────────────────

    def _http_probe(self, url: str) -> Optional[HttpProbe]:
        t0 = time.monotonic()
        probe = HttpProbe(url=url)
        redirects: list[str] = []

        class _NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                redirects.append(newurl)
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None
            opener = urllib.request.build_opener(_NoRedir)
            req    = urllib.request.Request(url, headers=_HEADERS, method="HEAD")
            ctx    = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            try:
                with opener.open(req, timeout=_TIMEOUT) as r:
                    probe.status       = r.status
                    probe.server       = r.headers.get("Server","")
                    probe.content_type = r.headers.get("Content-Type","")
                    probe.x_powered_by = r.headers.get("X-Powered-By","")
            except urllib.error.HTTPError as e:
                probe.status = e.code
            except urllib.error.URLError:
                pass
            probe.redirects = redirects

            # TLS fingerprint
            if parsed.scheme == "https" and parsed.hostname:
                try:
                    raw  = ssl.create_connection((parsed.hostname, 443), timeout=_TIMEOUT)
                    tls  = ctx.wrap_socket(raw, server_hostname=parsed.hostname)
                    cert = tls.getpeercert() or {}
                    probe.tls_version = tls.version() or ""
                    probe.tls_cipher  = (tls.cipher() or [""])[0]
                    issuer = dict(x[0] for x in cert.get("issuer",[]))
                    probe.tls_issuer  = issuer.get("organizationName","")
                    probe.tls_expiry  = cert.get("notAfter","")
                    tls.close()
                except Exception as te:
                    self._emit(f"[TEL] TLS: {te}")

            # Flags de suspeita
            reasons = []
            if re.search(r"https?://\d{1,3}(\.\d{1,3}){3}", url):
                reasons.append("URL com IP direto")
            for pat in (r"bit\.ly",r"t\.co",r"goo\.gl",r"tinyurl",r"cutt\.ly",r"ngrok"):
                if re.search(pat, url):
                    reasons.append(f"Encurtador/túnel: {pat}")
            for srv in ("werkzeug","flask","ruby","php/5","apache/2.2"):
                if srv in (probe.server or "").lower():
                    reasons.append(f"Servidor incomum: {probe.server}")
                    break
            if len(redirects) > 2:
                reasons.append(f"Cadeia de {len(redirects)} redirects")
            if probe.tls_issuer and any(x in probe.tls_issuer.lower() for x in ("self","localhost","unknown")):
                reasons.append(f"Certificado auto-assinado: {probe.tls_issuer}")
            if probe.tls_expiry:
                try:
                    exp = datetime.datetime.strptime(probe.tls_expiry, "%b %d %H:%M:%S %Y %Z")
                    if exp < datetime.datetime.utcnow():
                        reasons.append("Certificado TLS expirado")
                except Exception:
                    pass

            probe.suspeito        = bool(reasons)
            probe.motivo_suspeito = " | ".join(reasons)
            probe.latencia_ms     = (time.monotonic()-t0)*1000
            self._emit(f"[TEL] HTTP: {url[:50]} → {probe.status} ({probe.latencia_ms:.0f}ms)"
                       + (f" SUSPEITO: {probe.motivo_suspeito}" if probe.suspeito else ""))
            return probe
        except Exception as e:
            self._emit(f"[TEL] HTTP: {type(e).__name__}")
            return None

    # ── GeoIP ─────────────────────────────────────────────────────────

    def _geo_ip(self, url: str) -> dict:
        t0 = time.monotonic()
        try:
            host = urllib.parse.urlparse(url).hostname or ""
            if not host:
                return {}
            ip = host if re.match(r"\d{1,3}(\.\d{1,3}){3}",host) else socket.gethostbyname(host)
            fields = "status,country,countryCode,regionName,city,zip,lat,lon,isp,org,as,query"
            with urllib.request.urlopen(
                urllib.request.Request(f"http://ip-api.com/json/{ip}?fields={fields}", headers=_HEADERS),
                timeout=_TIMEOUT,
            ) as r:
                d = json.loads(r.read())
            ms = (time.monotonic()-t0)*1000
            if d.get("status") == "success":
                self._emit(f"[TEL] GeoIP: {ip} → {d.get('city')},{d.get('countryCode')} ISP={d.get('isp')} ({ms:.0f}ms)")
                return {**d, "ip":ip, "latencia_ms":ms}
        except Exception as e:
            self._emit(f"[TEL] GeoIP: {type(e).__name__}")
        return {}

    # ── PSP lookup ────────────────────────────────────────────────────

    def _psp_lookup(self, ispb: str) -> dict:
        k = ispb.zfill(8)
        if k in _PSP_DB:
            info = dict(_PSP_DB[k])
            info["ispb"] = ispb
            self._emit(f"[TEL] PSP local: {info['nome']}")
            return info
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(
                urllib.request.Request("https://brasilapi.com.br/api/banks/v1", headers=_HEADERS),
                context=ssl.create_default_context(),
                timeout=_TIMEOUT,
            ) as r:
                banks = json.loads(r.read())
            for b in banks:
                if str(b.get("code","")).zfill(8) == k:
                    ms = (time.monotonic()-t0)*1000
                    self._emit(f"[TEL] PSP BrasilAPI: {b.get('name')} ({ms:.0f}ms)")
                    return {"nome":b.get("fullName") or b.get("name",""), "ispb":ispb, "fonte":"BrasilAPI"}
        except Exception as e:
            self._emit(f"[TEL] PSP: {type(e).__name__}")
        return {}

    # ── Anomalias ─────────────────────────────────────────────────────

    def _detect_anomalies(self, report: TelemetryReport, meta: dict):
        anoms = []
        delta = 0

        cep_t = report.cep_triangulado
        cep_p = re.sub(r"\D","",report.cep_payload)

        if cep_p and cep_t and cep_t.cep and cep_p != re.sub(r"\D","",cep_t.cep):
            anoms.append(f"CEP do payload ({cep_p}) diverge do triangulado ({cep_t.cep})")
            delta -= 10

        if cep_t and meta.get("cidade"):
            cm = meta["cidade"].lower()
            cc = cep_t.cidade.lower()
            if cm and cc and cm not in cc and cc not in cm:
                anoms.append(f"Cidade declarada '{meta['cidade']}' difere do CEP triangulado '{cep_t.cidade}'")
                delta -= 8

        if report.http_probe and report.http_probe.suspeito:
            anoms.append(f"URL dinâmica suspeita: {report.http_probe.motivo_suspeito}")
            delta -= 15

        geo = report.geo_ip
        if geo.get("countryCode") and geo["countryCode"] != "BR":
            anoms.append(
                f"Host Pix sediado fora do Brasil: {geo.get('city')}, "
                f"{geo.get('countryCode')} (ISP: {geo.get('isp')})"
            )
            delta -= 20

        if report.dns and report.dns.ips and not report.dns.rdns:
            anoms.append("IP da URL sem DNS reverso — infraestrutura anônima")
            delta -= 5

        if report.http_probe and report.http_probe.latencia_ms > 4000:
            anoms.append(
                f"Latência HTTP alta ({report.http_probe.latencia_ms:.0f}ms) — possível honeypot"
            )
            delta -= 5

        report.anomalias   = anoms
        report.score_delta = delta
        for a in anoms:
            self._emit(f"[TEL] ⚑ Anomalia: {a}")

    # ── Helpers ───────────────────────────────────────────────────────

    def _safe(self, future: Optional[concurrent.futures.Future], name: str):
        if future is None:
            return None
        try:
            return future.result(timeout=0.5)
        except Exception as e:
            self._emit(f"[TEL] {name}: {type(e).__name__}")
            return None

    def _emit(self, msg: str):
        with self._lock:
            log.debug(msg)
        try:
            self._cb(msg)
        except Exception:
            pass

    def shutdown(self):
        self._executor.shutdown(wait=False)
