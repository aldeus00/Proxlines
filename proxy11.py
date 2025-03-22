import requests
import threading
import time
from termcolor import colored
import art

# 3D Kırmızı Banner
banner = art.text3d("EXELANS")
print(colored(banner, "red"))

# Proxy API Listesi (10+ API)
proxy_apis = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://api.openproxylist.xyz/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://www.proxyscan.io/download?type=http",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://proxyspace.pro/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
]

# Dosya isimleri
proxy_file = "cekildi.txt"
valid_proxy_file = "gecerli.txt"

# Test edilecek site
test_url = "http://www.google.com"

# Proxyleri kaydetme fonksiyonu
def save_proxies(proxies, filename):
    with open(filename, "w") as file:
        for proxy in proxies:
            file.write(proxy + "\n")

# Çalışan proxyleri yazma fonksiyonu
def save_valid_proxy(proxy):
    with open(valid_proxy_file, "a") as file:
        file.write(proxy + "\n")
    print(colored(f"[✓] Çalışan Proxy: {proxy}", "green"))

# Proxy kontrol fonksiyonu
def check_proxy(proxy):
    proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    try:
        response = requests.get(test_url, proxies=proxy_dict, timeout=5)
        if response.status_code == 200:
            save_valid_proxy(proxy)
    except:
        pass  # Geçersiz proxy'leri yazdırmıyoruz

# API'den proxy çekme fonksiyonu
def fetch_proxies():
    proxies = set()
    
    for api in proxy_apis:
        try:
            response = requests.get(api, timeout=10)
            if response.status_code == 200:
                new_proxies = response.text.splitlines()
                proxies.update(new_proxies)
                print(colored(f"[+] {api} API'sinden {len(new_proxies)} proxy alındı!", "cyan"))
        except:
            print(colored(f"[-] {api} API'sine ulaşılamadı!", "red"))

    print(colored(f"[!] Toplam {len(proxies)} proxy çekildi, 'cekildi.txt' dosyasına kaydediliyor...", "yellow"))
    
    # Proxyleri 'cekildi.txt' dosyasına yaz
    save_proxies(proxies, proxy_file)

# Çekilen proxyleri kontrol etme fonksiyonu
def check_proxies_from_file():
    try:
        with open(proxy_file, "r") as file:
            proxies = file.read().splitlines()
    except FileNotFoundError:
        print(colored("[-] 'cekildi.txt' dosyası bulunamadı! Önce proxy çekmelisiniz.", "red"))
        return
    
    print(colored(f"[!] {len(proxies)} proxy kontrol ediliyor...", "yellow"))

    # Proxyleri çoklu iş parçacığı (threading) ile kontrol et
    threads = []
    for proxy in proxies:
        thread = threading.Thread(target=check_proxy, args=(proxy,))
        thread.start()
        threads.append(thread)
        time.sleep(0.1)  # API kısıtlamalarını aşmak için bekleme süresi
    
    # Tüm thread'lerin tamamlanmasını bekle
    for thread in threads:
        thread.join()

    print(colored("[✓] Kontrol tamamlandı, geçerli proxyler 'gecerli.txt' dosyasına kaydedildi!", "green"))

# Çalıştırma Seçenekleri
if __name__ == "__main__":
    while True:
        print("\n[1] API'den Proxy Çek ve 'cekildi.txt' Dosyasına Kaydet")
        print("[2] 'cekildi.txt' Dosyasından Proxyleri Kontrol Et ve 'gecerli.txt' Kaydet")
        print("[3] Çıkış")
        
        secim = input("Seçiminizi yapın: ")
        
        if secim == "1":
            fetch_proxies()
        elif secim == "2":
            check_proxies_from_file()
        elif secim == "3":
            print(colored("[!] Çıkılıyor...", "red"))
            break
        else:
            print(colored("[-] Geçersiz seçenek! Lütfen 1, 2 veya 3 girin.", "red"))
