#@cantarellabots
"""Anikoto.cz scraper — search, episodes, and direct m3u8 download via MegaPlay."""
from cantarella.core.proxy import get_random_proxy, get_proxy_dict
from curl_cffi import requests as c_requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
import subprocess
import shutil
import json

BASE_URL = "https://anikoto.cz"
MEGAPLAY_BASE = "https://megaplay.buzz"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
}


class AnikotoScraper:
    def __init__(self, download_path="anime_downloads", progress_queue=None):
        self.download_path = Path(download_path)
        self.download_path.mkdir(exist_ok=True)
        self.progress_queue = progress_queue
        self.binary_path = self._get_binary_path()
        self.proxy = get_random_proxy()
        self.session = c_requests.Session()
        proxy_dict = get_proxy_dict(self.proxy)
        if proxy_dict:
            self.session.proxies.update(proxy_dict)

    def _get_binary_path(self):
        candidates = [
            Path("binary") / "N_m3u8DL-RE",
            Path("binary") / "N_m3u8DL-RE.exe",
            Path("/usr/local/bin/N_m3u8DL-RE"),
        ]
        for p in candidates:
            if p.exists():
                return p
        which_path = shutil.which("N_m3u8DL-RE")
        if which_path:
            return Path(which_path)
        return None

    def _get(self, url, **kwargs):
        headers = {**HEADERS, **kwargs.pop("headers", {})}
        return self.session.get(url, headers=headers, impersonate="chrome131", timeout=20, **kwargs)

    def search_anime(self, query):
        try:
            resp = self._get(
                f"{BASE_URL}/ajax/anime/search",
                params={"keyword": query},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            result = data.get("result") or {}
            html = result.get("html") if isinstance(result, dict) else result
            if not html:
                return []
            soup = BeautifulSoup(html, "html.parser")
            results = []
            seen = set()
            for a in soup.select('a[href*="/watch/"]'):
                href = a.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)
                slug = href.rstrip("/").split("/")[-1]
                title = a.get_text(" ", strip=True) or slug
                # Clean trailing meta like "PG-13 8.55 TV 2022"
                title = re.sub(r"(PG-13|R-17|G|R\+|Rx).*$", "", title).strip() or slug
                results.append({
                    "title": title,
                    "id": slug,
                    "type": "TV",
                    "url": href if href.startswith("http") else f"{BASE_URL}{href}",
                })
                if len(results) >= 12:
                    break
            return results
        except Exception as e:
            print(f"Anikoto search error: {e}")
            return []

    def _resolve_anime_id(self, anime_ref):
        """Accept slug URL or numeric id; return (numeric_id, slug, page_url)."""
        if isinstance(anime_ref, int) or (isinstance(anime_ref, str) and anime_ref.isdigit()):
            return str(anime_ref), str(anime_ref), f"{BASE_URL}/watch/{anime_ref}"

        slug = anime_ref
        if "/watch/" in anime_ref:
            slug = anime_ref.rstrip("/").split("/watch/")[-1].split("?")[0]
        page_url = f"{BASE_URL}/watch/{slug}"
        try:
            resp = self._get(page_url)
            m = re.search(r'data-id=["\'](\d+)["\']', resp.text)
            if m:
                return m.group(1), slug, page_url
        except Exception as e:
            print(f"Anikoto resolve id error: {e}")
        return None, slug, page_url

    def list_episodes(self, anime_ref):
        anime_id, slug, page_url = self._resolve_anime_id(anime_ref)
        if not anime_id:
            return []
        try:
            resp = self._get(
                f"{BASE_URL}/ajax/episode/list/{anime_id}",
                headers={"X-Requested-With": "XMLHttpRequest", "Referer": page_url},
            )
            if resp.status_code != 200:
                return []
            html = resp.json().get("result", "")
            soup = BeautifulSoup(html, "html.parser")
            results = []
            for a in soup.select("a[data-id]"):
                ep_num = a.get("data-num") or a.get("data-number") or a.get_text(strip=True)
                ep_id = a.get("data-id")
                data_ids = a.get("data-ids", "")
                results.append({
                    "title": f"Episode {ep_num}",
                    "url": f"{page_url}?ep={ep_num}",
                    "ep_number": str(ep_num),
                    "ep_id": ep_id,
                    "data_ids": data_ids,
                    "anime_id": anime_id,
                    "slug": slug,
                })
            return results
        except Exception as e:
            print(f"Anikoto list episodes error: {e}")
            return []

    def get_episode_servers(self, data_ids, referer=None):
        try:
            resp = self._get(
                f"{BASE_URL}/ajax/server/list",
                params={"servers": data_ids},
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": referer or f"{BASE_URL}/",
                },
            )
            if resp.status_code != 200:
                return []
            html = resp.json().get("result", "")
            soup = BeautifulSoup(html, "html.parser")
            servers = []
            for li in soup.select("li[data-link-id]"):
                servers.append({
                    "link_id": li.get("data-link-id"),
                    "sv_id": li.get("data-sv-id"),
                    "name": li.get_text(strip=True),
                    "ep_id": li.get("data-ep-id"),
                })
            return servers
        except Exception as e:
            print(f"Anikoto servers error: {e}")
            return []

    def get_embed_url(self, link_id, referer=None):
        try:
            resp = self._get(
                f"{BASE_URL}/ajax/server",
                params={"get": link_id},
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": referer or f"{BASE_URL}/",
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            result = data.get("result") or {}
            if isinstance(result, dict):
                return result.get("url")
            return None
        except Exception as e:
            print(f"Anikoto embed error: {e}")
            return None

    def extract_m3u8(self, embed_url):
        """Resolve MegaPlay (and similar) embed pages to a master m3u8."""
        try:
            resp = self._get(embed_url, headers={"Referer": f"{BASE_URL}/"})
            if resp.status_code != 200:
                return None
            # data-id on player element
            m = re.search(r'data-id=["\'](\d+)["\']', resp.text)
            file_id = m.group(1) if m else None
            if not file_id:
                # fallback: realid
                m2 = re.search(r'data-realid=["\'](\d+)["\']', resp.text)
                file_id = m2.group(1) if m2 else None
            if not file_id:
                return None

            # MegaPlay sources API
            src_resp = self._get(
                f"{MEGAPLAY_BASE}/stream/getSources",
                params={"id": file_id},
                headers={
                    "Referer": embed_url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": MEGAPLAY_BASE,
                },
            )
            if src_resp.status_code != 200:
                return None
            data = src_resp.json()
            sources = data.get("sources")
            if isinstance(sources, dict):
                return sources.get("file")
            if isinstance(sources, list) and sources:
                return sources[0].get("file") or sources[0].get("url")
            return None
        except Exception as e:
            print(f"Anikoto m3u8 extract error: {e}")
            return None

    def get_stream_for_episode(self, ep_entry):
        """Full chain: servers -> embed -> m3u8 for one episode dict from list_episodes."""
        data_ids = ep_entry.get("data_ids")
        referer = ep_entry.get("url") or f"{BASE_URL}/"
        if not data_ids:
            # re-fetch list to get data_ids
            eps = self.list_episodes(ep_entry.get("slug") or ep_entry.get("anime_id"))
            for e in eps:
                if str(e.get("ep_number")) == str(ep_entry.get("ep_number")):
                    data_ids = e.get("data_ids")
                    break
        if not data_ids:
            return None

        servers = self.get_episode_servers(data_ids, referer=referer)
        # Prefer HD-1 / Vidstream style servers
        preferred = sorted(
            servers,
            key=lambda s: (
                0 if "hd" in (s.get("name") or "").lower() else 1,
                0 if "vid" in (s.get("name") or "").lower() else 1,
            ),
        )
        for srv in preferred:
            embed = self.get_embed_url(srv["link_id"], referer=referer)
            if not embed:
                continue
            m3u8 = self.extract_m3u8(embed)
            if m3u8:
                return {"url": m3u8, "server": srv.get("name"), "embed": embed}
        return None

    def download_episode(self, url, quality="auto", name_override=None, season_override=None, ep_num_override=None):
        # Parse watch URL + ep=
        slug = url
        ep_num = ep_num_override or "1"
        if "/watch/" in url:
            part = url.split("/watch/")[-1]
            slug = part.split("?")[0]
            m = re.search(r"[?&]ep=(\d+)", url)
            if m:
                ep_num = m.group(1)

        eps = self.list_episodes(slug)
        if not eps:
            if self.progress_queue:
                self.progress_queue.put({"error": "No episodes found on Anikoto."})
            return False

        target = None
        for e in eps:
            if str(e.get("ep_number")) == str(ep_num):
                target = e
                break
        if not target:
            target = eps[0]
            ep_num = target.get("ep_number", ep_num)

        anime_name = name_override or slug.replace("-", " ").title()
        # Try to get a cleaner title from the watch page
        try:
            page = self._get(f"{BASE_URL}/watch/{slug}")
            t = re.search(r"<title>([^<]+)", page.text, re.I)
            if t:
                anime_name = name_override or t.group(1).split(" at ")[0].split(" | ")[0].strip()
        except Exception:
            pass

        if self.progress_queue:
            self.progress_queue.put({"status": f"📥 **Resolving stream (Anikoto): {anime_name} EP{ep_num}**"})

        stream = self.get_stream_for_episode(target)
        if not stream or not stream.get("url"):
            if self.progress_queue:
                self.progress_queue.put({"error": "Could not resolve m3u8 from Anikoto/MegaPlay."})
            return False

        m3u8_url = stream["url"]
        qual_str = quality if quality and quality != "auto" else "1080"

        def sanitize(name):
            return re.sub(r'[\\/*?:"<>|]', "", name)

        try:
            from config import FORMAT
        except ImportError:
            FORMAT = "[E{episode}] {title} [{quality}] [{audio}]"

        base_filename = sanitize(
            FORMAT.format(
                season=season_override or "1",
                episode=ep_num_override or ep_num,
                title=anime_name,
                quality=f"{qual_str}p" if str(qual_str).isdigit() else str(qual_str),
                audio="JP",
            )
        )

        if not self.binary_path:
            if self.progress_queue:
                self.progress_queue.put({"error": "N_m3u8DL-RE binary not found."})
            return False

        task_dir = self.download_path / f"anikoto_{slug}_{ep_num}"
        task_dir.mkdir(exist_ok=True)
        final_file = self.download_path / f"{base_filename}.mkv"

        if self.progress_queue:
            self.progress_queue.put({"status": f"📥 **Downloading (Anikoto): {anime_name} EP{ep_num}**\nPlease wait..."})

        cmd = [
            str(self.binary_path),
            m3u8_url,
            "--save-dir",
            str(task_dir),
            "--save-name",
            base_filename,
            "-H",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-H",
            f"Referer: {MEGAPLAY_BASE}/",
            "-H",
            f"Origin: {MEGAPLAY_BASE}",
            "--check-segments-count",
            "False",
            "-mt",
            "--thread-count",
            "32",
            "--download-retry-count",
            "5",
            "--auto-select",
        ]
        if self.proxy:
            cmd.extend(["--custom-proxy", self.proxy])

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        while True:
            line = process.stdout.readline()
            if not line:
                break
            line = line.decode("utf-8", errors="replace").strip()
            if "%" in line and self.progress_queue:
                percent_match = re.search(r"(\d+(\.\d+)?)%", line)
                if percent_match:
                    speed_match = re.search(r"(\d+(\.\d+)?\s*[MKG]?i?(B/s|bps))", line, re.I)
                    size_match = re.search(r"(\d+(\.\d+)?\s*\S+)\s*/\s*(\d+(\.\d+)?\s*\S+)", line, re.I)
                    self.progress_queue.put({
                        "percent": f"{percent_match.group(1)}%",
                        "speed": speed_match.group(1) if speed_match else "0 MB/s",
                        "downloaded": size_match.group(1) if size_match else "?",
                        "total": size_match.group(3) if size_match else "?",
                        "type": "sub",
                        "title": f"Episode {ep_num}",
                    })
        process.wait()

        # Find output file
        out = None
        for f in task_dir.iterdir():
            if f.is_file() and f.suffix.lower() in {".mp4", ".mkv", ".ts"}:
                out = f
                break
        if not out:
            if self.progress_queue:
                self.progress_queue.put({"error": "Download finished but file missing."})
            shutil.rmtree(task_dir, ignore_errors=True)
            return False

        out.replace(final_file)
        shutil.rmtree(task_dir, ignore_errors=True)
        if self.progress_queue:
            self.progress_queue.put({"finished": True, "filename": str(final_file), "title": base_filename})
        return True


if __name__ == "__main__":
    s = AnikotoScraper()
    print(s.search_anime("naruto")[:3])
    eps = s.list_episodes("naruto-shippuden-c8gov")
    print("eps", len(eps), eps[0] if eps else None)
    if eps:
        stream = s.get_stream_for_episode(eps[0])
        print("stream", stream)
