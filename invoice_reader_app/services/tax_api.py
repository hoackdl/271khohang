import requests

def lookup_tax_code(mst: str):
    """
    Trả về dict hoặc None
    """
    url = f"https://api.vietqr.io/v2/business/{mst}"

    try:
        r = requests.get(url, timeout=5)
        data = r.json()

        if data.get("code") != "00":
            return None

        biz = data["data"]
        return {
            "ten_khach_hang": biz.get("name", ""),
            "dia_chi": biz.get("address", ""),
        }
    except Exception:
        return None
