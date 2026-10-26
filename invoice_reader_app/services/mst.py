import os
import time
from datetime import datetime
import base64
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.common.by import By


def tra_cuu_mst_selenium(mst: str):
    """
    Tra cứu MST từ website Tổng cục Thuế
    - Lấy tên + địa chỉ
    - Chụp ảnh kết quả
    - Trả về dict để lưu DB
    """

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # chạy ngầm
    options.add_argument("--window-size=1200,900")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://tracuunnt.gdt.gov.vn/tcnnt/mstdn.jsp")

        if not hasattr(tra_cuu_mst_selenium, "captcha_done"):
            input("👉 Nhập captcha lần đầu rồi Enter...")
            tra_cuu_mst_selenium.captcha_done = True

        # nhập MST
        mst_input = driver.find_element(By.NAME, "mst")
        mst_input.clear()
        mst_input.send_keys(mst)

        driver.find_element(By.NAME, "search").click()

        time.sleep(3)

        # =========================
        # LẤY DỮ LIỆU
        # =========================
        try:
            ten = driver.find_element(By.XPATH, "//table//tr[2]/td[2]").text
        except:
            ten = ""

        try:
            dia_chi = driver.find_element(By.XPATH, "//table//tr[3]/td[2]").text
        except:
            dia_chi = ""

        # =========================
        # CHỤP ẢNH (chuẩn MEDIA_ROOT)
        # =========================
        folder = os.path.join(settings.MEDIA_ROOT, "mst")
        os.makedirs(folder, exist_ok=True)

        filename = f"{mst}_{int(time.time())}.png"
        file_path = os.path.join(folder, filename)

        try:
            table = driver.find_element(By.XPATH, "//table")
            table.screenshot(file_path)
        except:
            driver.save_screenshot(file_path)
                # đọc file ảnh
        with open(file_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")    


            
        return {
            "ten": ten,
            "dia_chi": dia_chi,
            "image": f"mst/{filename}",  # ✔ lưu DB dạng relative path
            "image_base64": img_base64,
            "checked_at": datetime.now()
        }






    except Exception as e:
        print(f"❌ Lỗi tra cứu MST {mst}: {e}")
        return {
            "ten": "",
            "dia_chi": "",
            "image": "",
            "checked_at": datetime.now()
        }

    finally:
        driver.quit()

        