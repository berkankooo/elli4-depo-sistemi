import streamlit as st
import pandas as pd
import json
import os
import requests
import time
from datetime import datetime
import streamlit.components.v1 as components

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_KURULU = True
except ImportError:
    FIREBASE_KURULU = False

DB_FILE = "festival_depo_saha_data.json"
LOGO_FILE_1 = "logo.jpg"
TELEGRAM_BOT_TOKEN = "8889188919:AAEGQiGOosknNTq_3QbbIXdi4-IDsU3lXdU"
TELEGRAM_CHAT_ID = "-1003743777112"

FIREBASE_DB_URL = "https://elli4-event-depo-default-rtdb.firebaseio.com/"

st.set_page_config(page_title="Elli4 Event - Sakarya Festivali", layout="wide")

if FIREBASE_KURULU and FIREBASE_DB_URL:
    if not firebase_admin._apps:
        try:
            key_dict = json.loads(st.secrets["firebase_key"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_DB_URL
            })
            FIREBASE_AKTIF = True
        except Exception as e:
            st.error(f"Firebase Cloud Güvenlik Kasası Bağlantı Hatası: {e}")
            FIREBASE_AKTIF = False
    else:
        FIREBASE_AKTIF = True
else:
    FIREBASE_AKTIF = False

def telegram_mesaj_gonder(mesaj):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "BOT_TOKENINIZI_BURAYA_YAZIN":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
        try: requests.post(url, json=payload, timeout=5)
        except Exception: pass

def varsayilan_veri_yapisi():
    return {
        "depo_stok": {}, 
        "barlar_yeni": {}, 
        "barlar": {},      
        "zayiatlar": [], "free_cikislar": [], "kokteyl_tanimlari": {}, "rapor_arsivi": [],
        "depo_loglari": [], "transfer_loglari": [],
        "onay_bekleyen_transferler": [],
        "supervisors": {} 
    }

def datetime_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    raise TypeError("Type not serializable")

def veri_yukle():
    if FIREBASE_AKTIF:
        try:
            ref = db.reference('/')
            d = ref.get()
            if d is not None:
                if "depo_loglari" not in d: d["depo_loglari"] = []
                if "transfer_loglari" not in d: d["transfer_loglari"] = []
                if "barlar_yeni" not in d: d["barlar_yeni"] = {}
                if "zayiatlar" not in d: d["zayiatlar"] = []
                if "free_cikislar" not in d: d["free_cikislar"] = []
                if "onay_bekleyen_transferler" not in d: d["onay_bekleyen_transferler"] = []
                if "supervisors" not in d: d["supervisors"] = {}
                return d
        except Exception as e:
            st.warning(f"Sistem bulut bağlantısında sorun yaşadı, yerel yedeğe dönülüyor... Hata: {e}")
            
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            if "depo_loglari" not in d: d["depo_loglari"] = []
            if "transfer_loglari" not in d: d["transfer_loglari"] = []
            if "barlar_yeni" not in d: d["barlar_yeni"] = {}
            if "zayiatlar" not in d: d["zayiatlar"] = []
            if "free_cikislar" not in d: d["free_cikislar"] = []
            if "onay_bekleyen_transferler" not in d: d["onay_bekleyen_transferler"] = []
            if "supervisors" not in d: d["supervisors"] = {}
            return d
    return varsayilan_veri_yapisi()

def veri_kaydet(data):
    safe_data = json.loads(json.dumps(data, default=datetime_serializer))
    if FIREBASE_AKTIF:
        try:
            ref = db.reference('/')
            ref.set(safe_data)
        except Exception as e:
            st.error(f"Bulut senkronizasyon hatası: {e}")
            
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=datetime_serializer)

if "data" not in st.session_state:
    st.session_state.data = veri_yukle()

data = st.session_state.data
GUN_SECIMLERI = ["1. Gün", "2. Gün", "3. Gün"]

def dev_bildirim_goster(durum, baslik, mesaj_metni=""):
    bg_color = "#333333" if durum == "basarili" else "#990000"
    html_kod = f"""
    <div id="dev-modal-overlay" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.8); z-index: 99999; display: flex; justify-content: center; align-items: center;">
        <div style="background-color: #ffffff; border: 2px solid {bg_color}; border-radius: 4px; padding: 40px; text-align: center; max-width: 500px; width: 90%; box-shadow: 0px 4px 20px rgba(0,0,0,0.2); color: #000000;">
            <div style="font-size: 28px; font-weight: 700; margin-bottom: 12px;">{baslik.upper()}</div>
            <div style="font-size: 16px; color: #555555; line-height: 1.6;">{mesaj_metni}</div>
        </div>
    </div>
    """
    placeholder = st.empty()
    placeholder.markdown(html_kod, unsafe_allow_html=True)
    time.sleep(2.5)
    placeholder.empty()

def get_bar_listesi(tur_filtresi):
    return [bar for bar, tur in data["barlar_yeni"].items() if tur == tur_filtresi]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.active_user_fullname = ""
    st.session_state.active_username = ""

js_session_catcher = """
<script>
    const token = localStorage.getItem("elli4_auth_token");
    const role = localStorage.getItem("elli4_auth_role");
    const fullname = localStorage.getItem("elli4_auth_fullname");
    const username = localStorage.getItem("elli4_auth_username");
    
    if (token === "true" && !window.location.search.includes("loaded=true")) {
        const url = new URL(window.location.href);
        url.searchParams.set("token", token);
        url.searchParams.set("role", role);
        url.searchParams.set("fullname", fullname);
        url.searchParams.set("username", username);
        url.searchParams.set("loaded", "true");
        window.parent.location.href = url.href;
    }
</script>
"""
components.html(js_session_catcher, height=0, width=0)

query_params = st.query_params
if "token" in query_params and query_params["token"] == "true" and not st.session_state.authenticated:
    st.session_state.authenticated = True
    st.session_state.user_role = query_params["role"]
    st.session_state.active_user_fullname = query_params["fullname"]
    st.session_state.active_username = query_params["username"]

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(LOGO_FILE_1):
            st.image(LOGO_FILE_1, use_container_width=True)
        st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>Elli4 Event</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #888888; margin-top: 0px;'>Sakarya Festivali Yönetim Paneli</h4>", unsafe_allow_html=True)
        st.write("") 
        with st.form("login_form"):
            st.markdown("<p style='text-align: center;'>Sisteme erişmek için lütfen giriş yapınız.</p>", unsafe_allow_html=True)
            username_input = st.text_input("Kullanıcı Adı").strip().lower()
            password_input = st.text_input("Şifre", type="password").strip()
            btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
            with btn_col2:
                submit_btn = st.form_submit_button("Giriş Yap", use_container_width=True)
            if submit_btn:
                role, fullname, valid = "", "", False
                if username_input == "depocu" and password_input == "depo123":
                    role, fullname, valid = "depocu", "Merkez Depo Sorumlusu", True
                elif username_input == "kontrol" and password_input == "kontrol123":
                    role, fullname, valid = "kontrolcu", "Kontrolcü", True
                elif username_input in data["supervisors"] and data["supervisors"][username_input]["password"] == password_input:
                    role, fullname, valid = "supervisor", f"{data['supervisors'][username_input]['name']} {data['supervisors'][username_input]['surname']}", True
                if valid:
                    st.session_state.authenticated = True
                    st.session_state.user_role = role
                    st.session_state.active_user_fullname = fullname
                    st.session_state.active_username = username_input
                    js_login_injector = f"""
                    <script>
                        localStorage.setItem("elli4_auth_token", "true");
                        localStorage.setItem("elli4_auth_role", "{role}");
                        localStorage.setItem("elli4_auth_fullname", "{fullname}");
                        localStorage.setItem("elli4_auth_username", "{username_input}");
                        setTimeout(() => {{
                            const url = new URL(window.parent.location.href);
                            url.searchParams.set("token", "true");
                            url.searchParams.set("role", "{role}");
                            url.searchParams.set("fullname", "{fullname}");
                            url.searchParams.set("username", "{username_input}");
                            url.searchParams.set("loaded", "true");
                            window.parent.location.href = url.href;
                        }}, 100);
                    </script>
                    """
                    components.html(js_login_injector, height=0, width=0)
                    st.success("Giriş başarılı, yönetim paneline yönlendiriliyorsunuz...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

if os.path.exists(LOGO_FILE_1):
    st.sidebar.image(LOGO_FILE_1, use_container_width=True)

if FIREBASE_AKTIF:
    st.sidebar.success("🟢 Bulut Veritabanı: AKTİF")
else:
    st.sidebar.warning("🔴 Bulut Veritabanı: KAPALI (Yerel Mod)")

st.sidebar.markdown("---")
if st.sidebar.button("Oturumu Kapat"):
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.active_user_fullname = ""
    st.session_state.active_username = ""
    js_logout_injector = """
    <script>
        localStorage.removeItem("elli4_auth_token");
        localStorage.removeItem("elli4_auth_role");
        localStorage.removeItem("elli4_auth_fullname");
        localStorage.removeItem("elli4_auth_username");
        setTimeout(() => {
            const url = new URL(window.parent.location.href);
            url.searchParams.delete("token");
            url.searchParams.delete("role");
            url.searchParams.delete("fullname");
            url.searchParams.delete("username");
            url.searchParams.delete("loaded");
            window.parent.location.href = url.origin + url.pathname;
        }, 100);
    </script>
    """
    components.html(js_logout_injector, height=0, width=0)
    st.info("Oturum kapatılıyor...")
    time.sleep(0.5)
    st.rerun()

def sayfa_depo_takip():
    st.title("Saha Sevkiyat Takip Ekranı")
    tab_bekleyen, tab_onaylanan = st.tabs(["Onay Bekleyen Sevkiyatlar", "Tamamlanan Sevkiyatlar"])
    with tab_bekleyen:
        bekleyenler = [t for t in data["onay_bekleyen_transferler"] if t["onaylandi"] == False]
        if not bekleyenler: st.info("Şu an onay bekleyen irsaliye bulunmuyor.")
        else: st.dataframe(pd.DataFrame(bekleyenler), use_container_width=True)
    with tab_onaylanan:
        onaylananlar = [t for t in data["onay_bekleyen_transferler"] if t["onaylandi"] == True]
        if not onaylananlar: st.info("Henüz onaylanmış sevkiyat bulunmuyor.")
        else: st.dataframe(pd.DataFrame(onaylananlar), use_container_width=True)

def sayfa_supervisor_kabul():
    st.title("İstasyon Mal Kabul Sistemi")
    st.write(f"Sorumlu Supervisor: {st.session_state.active_user_fullname}")
    aktif_sevkler = [t for t in data["onay_bekleyen_transferler"] if t["onaylandi"] == False and t.get("hedef_supervisor_username") == st.session_state.active_username]
    if not aktif_sevkler:
        st.info("Adınıza bekleyen aktif bir sevk irsaliyesi bulunmamaktadır.")
        return
    sevk_idleri = list(set([t["sevk_kodu"] for t in aktif_sevkler]))
    for sevk_kodu in sevk_idleri:
        kalemler = [t for t in aktif_sevkler if t["sevk_kodu"] == sevk_kodu]
        bar_ismi = kalemler[0]["hedef"].upper()
        sup_isim = st.session_state.active_user_fullname.upper()
        fest_gunu = kalemler[0]["gün"].upper()
        islem_saati = kalemler[0].get("sevk_saati", datetime.now().strftime("%H:%M"))
        irsaliye_etiketi = f"{bar_ismi} - {sup_isim} - {fest_gunu} - {islem_saati}"
        with st.expander(irsaliye_etiketi, expanded=False):
            depodan_cikaran = kalemler[0].get("depocu_yetkili", "Merkez Depo")
            st.write(f"İrsaliyeyi Düzenleyen Depocu: {depodan_cikaran} | Kayıt Tarihi: {kalemler[0]['tarih']}")
            with st.form(f"form_kabul_{sevk_kodu}"):
                st.write("Fiziki Kör Sayım Adetlerini Giriniz:")
                super_sayimlari = {}
                for kalem in kalemler:
                    urun = kalem["urun"]
                    super_sayimlari[urun] = st.number_input(f"Sayılan Net Adet ({urun})", min_value=0, value=None, placeholder="Miktar giriniz...", step=1, key=f"sayim_{sevk_kodu}_{urun}")
                if st.form_submit_button("Malı Teslim Al"):
                    toplu_telegram_notu = f"[İSTASYON MAL KABUL RAPORU]\nİstasyon: {kalemler[0]['hedef']}\nTeslim Alan Supervisor: {st.session_state.active_user_fullname}\nDepodan Çıkaran: {depodan_cikaran}\nZaman: {kalemler[0]['gün']} - {islem_saati}\nİrsaliye Kodu: {sevk_kodu}\n\nMutabakat Detayları:\n"
                    for kalem in kalemler:
                        urun = kalem["urun"]
                        depo_yolladi = kalem["miktar"]
                        super_saydi = super_sayimlari[urun] if super_sayimlari[urun] is not None else 0
                        fark = super_saydi - depo_yolladi
                        data["barlar"][kalem["hedef"]][urun] = data["barlar"][kalem["hedef"]].get(urun, 0) + depo_yolladi
                        t_id = len(data["transfer_loglari"]) + 1
                        data["transfer_loglari"].append({"id": t_id, "gün": kalem["gün"], "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "kaynak": "Merkez Depo", "hedef": kalem["hedef"], "urun": urun, "miktar": depo_yolladi, "supervisor_sayim": super_saydi, "fark": fark, "depocu_yetkili": depodan_cikaran, "supervisor_yetkili": st.session_state.active_user_fullname, "iptal": False})
                        toplu_telegram_notu += f"Ürün: {urun} | Depo: {depo_yolladi} | Saha Sayım: {super_saydi} | FARK: {fark}\n"
                        for t in data["onay_bekleyen_transferler"]:
                            if t["sevk_kodu"] == sevk_kodu and t["urun"] == urun:
                                t["onaylandi"] = True
                    veri_kaydet(data)
                    telegram_mesaj_gonder(toplu_telegram_notu)
                    dev_bildirim_goster("basarili", "İşlem Tamamlandı", "Supervisor sayımı kaydedildi.")
                    st.rerun()

def sayfa_supervisor_tanimlama():
    st.title("Supervisor Personel Havuzu")
    with st.form("yeni_supervisor_form", clear_on_submit=True):
        st.write("Yeni Saha Şefi Tanımla")
        c1, c2 = st.columns(2)
        with c1: s_name = st.text_input("İsim")
        with c2: s_surname = st.text_input("Soyisim")
        c3, c4 = st.columns(2)
        with c3: s_user = st.text_input("Giriş Kullanıcı Adı").strip().lower()
        with c4: s_pass = st.text_input("Giriş Şifresi", type="password").strip()
        if st.form_submit_button("Personeli Veritabanına Kaydet"):
            if s_name and s_surname and s_user and s_pass:
                if s_user not in data["supervisors"] and s_user != "depocu":
                    data["supervisors"][s_user] = {"name": s_name.strip().title(), "surname": s_surname.strip().upper(), "password": s_pass}
                    veri_kaydet(data)
                    st.rerun()
                else: st.error("Bu kullanıcı adı zaten mevcut!")
            else: st.error("Lütfen tüm alanları doldurunuz!")
    st.write("Sistemde Kayıtlı Supervisor Listesi")
    if data["supervisors"]:
        sup_list = [{"Kullanıcı Adı": k, "İsim": v["name"], "Soyisim": v["surname"]} for k, v in data["supervisors"].items()]
        st.dataframe(pd.DataFrame(sup_list), use_container_width=True)
        silinecek_sup = st.selectbox("Yetkisi iptal edilecek supervisor:", list(data["supervisors"].keys()))
        if st.button("Seçilen Personeli Sil"):
            del data["supervisors"][silinecek_sup]
            veri_kaydet(data)
            st.rerun()

def sayfa_bar_tanimlama():
    st.title("İstasyon Yapılandırma")
    with st.form("yeni_bar_ekle_form", clear_on_submit=True):
        yeni_bar_adi = st.text_input("İstasyon / Bar Adı")
        bar_turu = st.selectbox("İstasyon Kategorisi:", ["Efes", "Red Bull", "Su"])
        if st.form_submit_button("İstasyonu Veritabanına Ekle"):
            if yeni_bar_adi:
                yeni_bar_adi = yeni_bar_adi.strip()
                if yeni_bar_adi not in data["barlar_yeni"]:
                    data["barlar_yeni"][yeni_bar_adi] = bar_turu
                    if yeni_bar_adi not in data["barlar"]: data["barlar"][yeni_bar_adi] = {}
                    veri_kaydet(data)
                    st.rerun()
                else: st.error("Bu istasyon ismi zaten mevcut!")
            else: st.error("Lütfen istasyon adı giriniz!")
    st.write("Tanımlı İstasyonlar")
    if data["barlar_yeni"]:
        bar_df = pd.DataFrame(list(data["barlar_yeni"].items()), columns=["İstasyon Adı", "Tür"])
        st.dataframe(bar_df, use_container_width=True)
        silinecek_bar = st.selectbox("Sistemden kaldırılacak istasyon:", list(data["barlar_yeni"].keys()))
        if st.button("Seçili İstasyonu Kaldır"):
            del data["barlar_yeni"][silinecek_bar]
            if silinecek_bar in data["barlar"]: del data["barlar"][silinecek_bar]
            veri_kaydet(data)
            st.rerun()

def sayfa_depo_yonetimi():
    st.title("Merkez Depo Envanter Girişi")
    if not data["depo_stok"]:
        st.info("Depo envanteri boş. Lütfen yeni ürün tanımlayınız.")
        islem_turu = "Sisteme Sıfırdan Yeni Ürün Tanımla"
    else:
        islem_turu = st.radio("İşlem Seçimi:", ["Mevcut Ürünün Stoğunu Arttır", "Sisteme Sıfırdan Yeni Ürün Tanımla"], horizontal=True)
    if islem_turu == "Mevcut Ürünün Stoğunu Arttır" and data["depo_stok"]:
        with st.form("mevcut_urun_form", clear_on_submit=True):
            secilen_gun = st.selectbox("İşlem Günü", GUN_SECIMLERI)
            secilen_urun = st.selectbox("Giriş Yapılacak Ürün", list(data["depo_stok"].keys()))
            girilen_koli = st.number_input("Koli Sayısı", min_value=0, value=None, placeholder="Miktar...", step=1)
            girilen_ek_adet = st.number_input("Ekstra Adet/Şişe", min_value=0, value=None, placeholder="Miktar...", step=1)
            if st.form_submit_button("Envanter Stoğunu Güncelle"):
                koli_val = girilen_koli if girilen_koli is not None else 0
                adet_val = girilen_ek_adet if girilen_ek_adet is not None else 0
                grup_turu = data["depo_stok"][secilen_urun]["grup"]
                toplam_fiziksel = (koli_val * data["depo_stok"][secilen_urun]["koli_ici"]) + adet_val
                eklenecek = toplam_fiziksel * data["depo_stok"][secilen_urun]["cl"] if grup_turu == "Ağır Alkol" else toplam_fiziksel
                data["depo_stok"][secilen_urun]["adet"] += eklenecek
                data["depo_loglari"].append({"id": len(data["depo_loglari"])+1, "gün": secilen_gun, "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "islem_tipi": "Stok Arttırma", "urun": secilen_urun, "miktar": eklenecek, "birim": "CL" if grup_turu == "Ağır Alkol" else "Adet", "iptal": False})
                veri_kaydet(data); st.rerun()
    else:
        with st.form("yeni_urun_form", clear_on_submit=True):
            yeni_urun_adi = st.text_input("Katalog Ürün Adı")
            grup = st.selectbox("Ürün Grubu:", ["Bira", "Ağır Alkol", "Yumuşak Alkol", "Enerji/Mikser", "Soft Drink", "Diğer"])
            birim = st.selectbox("Paketleme Birimi:", ["Kutu", "Şişe", "Fıçı", "Bardak"])
            koli_ici = st.number_input("1 Kolideki Adet?", min_value=1, value=None, placeholder="Adet...", step=1)
            cl_degeri = st.number_input("Hacim / CL Değeri", min_value=1, value=None, placeholder="Hacim...", step=1)
            if st.form_submit_button("Ürünü Kataloğa Ekle"):
                koli_val = koli_ici if koli_ici is not None else 24
                cl_val = cl_degeri if cl_degeri is not None else 100
                if yeni_urun_adi and yeni_urun_adi not in data["depo_stok"]:
                    data["depo_stok"][yeni_urun_adi] = {"grup": grup, "birim": birim, "adet": 0, "koli_ici": koli_val, "cl": cl_val}
                    veri_kaydet(data); st.rerun()
                else: st.error("Geçersiz veya envanterde mevcut ürün.")
    st.write("Merkez Depo Stok Durumu")
    if data["depo_stok"]:
        depo_df = pd.DataFrame.from_dict(data["depo_stok"], orient='index').reset_index().rename(columns={'index': 'Ürün Adı'})
        st.dataframe(depo_df, use_container_width=True)

def sayfa_depo_gecmisi():
    st.title("Envanter Hareket Geçmişi")
    filtre_gun = st.selectbox("Gün Seçimi", ["Tüm Günler"] + GUN_SECIMLERI)
    if data["depo_loglari"]:
        df = pd.DataFrame(data["depo_loglari"])
        if filtre_gun != "Tüm Günler": df = df[df["gün"] == filtre_gun]
        st.dataframe(df, use_container_width=True)

def jenerik_bar_stogu_goster(bar_listesi, izin_verilen_gruplar, baslik_kodu):
    st.title(baslik_kodu)
    if not bar_listesi:
        st.warning("Bu kategoriye ait tanımlı istasyon bulunmuyor.")
        return
    filtreli_urunler = [u for u, d in data["depo_stok"].items() if d["grup"] in izin_verilen_gruplar]
    if not filtreli_urunler:
        st.info("Bu katmana gösterilebilecek katalog ürünü bulunmuyor.")
        return
    for bar in bar_listesi:
        st.subheader(f"📍 {bar} Stok Durumu")
        bar_stok = data["barlar"].get(bar, {})
        gosterilecek_veri = []
        for urun in filtreli_urunler:
            gosterilecek_veri.append({"Ürün Adı": urun, "Mevcut Stok": bar_stok.get(urun, 0)})
        if gosterilecek_veri:
            st.dataframe(pd.DataFrame(gosterilecek_veri), use_container_width=True)
        else:
            st.write("Veri bulunamadı.")

def jenerik_transfer_yonetimi_sekmeli(bar_listesi, izin_verilen_gruplar, baslik_kodu):
    st.title(f"{baslik_kodu.replace('_', ' ')} Dağıtım Paneli")
    if not bar_listesi:
        st.warning("Bu katmana ait tanımlı istasyon bulunmuyor.")
        return
    if not data["supervisors"]:
        st.error("İşlem yapabilmek için öncelikle sistemde en az bir supervisor tanımlamalısınız!")
        return
    filtreli_urunler = [u for u, d in data["depo_stok"].items() if d["grup"] in izin_verilen_gruplar]
    if not filtreli_urunler:
        st.info("Bu katmana sevk edilebilecek katalog ürünü bulunmuyor.")
        return
    tab1, tab2, tab3 = st.tabs(["Depodan İstasyona Çoklu Sevk", "İstasyondan Depoya İade", "İstasyonlar Arası Sevkiyat"])
    with tab1:
        st.write("İrsaliye Düzenleme Paneli")
        secilen_gun = st.selectbox("Gün", GUN_SECIMLERI, key=f"g_d2b_{baslik_kodu}")
        hedef = st.selectbox("Alıcı İstasyon", bar_listesi, key=f"h_d2b_{baslik_kodu}")
        sup_secenekleri = list(data["supervisors"].keys())
        sup_yazilari = [f"{data['supervisors'][k]['name']} {data['supervisors'][k]['surname']}" for k in sup_secenekleri]
        sup_mapping = dict(zip(sup_yazilari, sup_secenekleri))
        secilen_sup_yazi = st.selectbox("Malı Sahada Karşılayacak Supervisor", sup_yazilari, key=f"s_d2b_{baslik_kodu}")
        hedef_sup_username = sup_mapping[secilen_sup_yazi]
        hedef_sup_fullname = secilen_sup_yazi
        secilen_urunler = st.multiselect("İrsaliyeye Eklenecek Ürünler", filtreli_urunler, key=f"multi_d2b_{baslik_kodu}")
        if secilen_urunler:
            st.write("Sevk Adetlerini Giriniz:")
            sevk_listesi = []
            for u in secilen_urunler:
                g_turu = data["depo_stok"][u]["grup"]
                if g_turu == "Ağır Alkol":
                    c1, c2 = st.columns(2)
                    with c1: s = st.number_input(f"{u} (Şişe)", min_value=0, value=None, placeholder="Şişe...", key=f"s_d2b_{u}")
                    with c2: c = st.number_input(f"{u} (CL)", min_value=0, value=None, placeholder="CL...", key=f"cl_d2b_{u}")
                    tot = ((s if s is not None else 0) * data["depo_stok"][u]["cl"]) + (c if c is not None else 0)
                    sevk_listesi.append({"urun": u, "miktar": tot, "grup": g_turu})
                else:
                    c1, c2 = st.columns(2)
                    with c1: k = st.number_input(f"{u} (Koli)", min_value=0, value=None, placeholder="Koli...", key=f"k_d2b_{u}")
                    with c2: a = st.number_input(f"{u} (Adet)", min_value=0, value=None, placeholder="Adet...", key=f"a_d2b_{u}")
                    tot = ((k if k is not None else 0) * data["depo_stok"][u]["koli_ici"]) + (a if a is not None else 0)
                    sevk_listesi.append({"urun": u, "miktar": tot, "grup": g_turu})
            if st.button("İrsaliyeyi Onayla ve Yola Çıkar", key=f"btn_d2b_{baslik_kodu}"):
                for kl in sevk_listesi:
                    if kl["miktar"] <= 0: continue
                    data["depo_stok"][kl["urun"]]["adet"] -= kl["miktar"]
                    data["onay_bekleyen_transferler"].append({"sevk_kodu": f"SRV-{int(time.time())}", "gün": secilen_gun, "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "sevk_saat": datetime.now().strftime("%H:%M"), "kaynak": "Merkez Depo", "hedef": hedef, "urun": kl["urun"], "miktar": kl["miktar"], "hedef_supervisor_username": hedef_sup_username, "yetkili": "Saha Ekibi", "depocu_yetkili": st.session_state.active_user_fullname, "onaylandi": False})
                veri_kaydet(data); st.rerun()
    with tab2:
        kaynak = st.selectbox("Çıkış Yapacak İstasyon", bar_listesi, key=f"k_b2d_{baslik_kodu}")
        teslim_alan = st.text_input("İadeyi Alan Depo Görevlisi", key=f"y_b2d_{baslik_kodu}")
        secilen_urunler = st.multiselect("İade Kaydı Açılacak Ürünler", filtreli_urunler, key=f"multi_b2d_{baslik_kodu}")
        if secilen_urunler:
            sevk_listesi = []
            for u in secilen_urunler:
                g_turu = data["depo_stok"][u]["grup"]
                if g_turu == "Ağır Alkol":
                    c1, c2 = st.columns(2)
                    with c1: s = st.number_input("Şişe", min_value=0, value=None, placeholder="Miktar...", key=f"s_b2d_{u}")
                    with c2: c = st.number_input("CL", min_value=0, value=None, placeholder="CL...", key=f"cl_b2d_{u}")
                    tot = ((s if s is not None else 0) * data["depo_stok"][u]["cl"]) + (c if c is not None else 0)
                    sevk_listesi.append({"urun": u, "miktar": tot, "grup": g_turu})
                else:
                    c1, c2 = st.columns(2)
                    with c1: k = st.number_input("Koli", min_value=0, value=None, placeholder="Koli...", key=f"k_b2d_{u}")
                    with c2: a = st.number_input(f"{u} (Adet)", min_value=0, value=None, placeholder="Adet...", key=f"a_b2d_{u}")
                    tot = ((k if k is not None else 0) * data["depo_stok"][u]["koli_ici"]) + (a if a is not None else 0)
                    sevk_listesi.append({"urun": u, "miktar": tot, "grup": g_turu})
            if st.button("İadeleri Onayla", key=f"btn_b2d_{baslik_kodu}"):
                for kl in sevk_listesi:
                    if kl["miktar"] <= 0: continue
                    data["barlar"][kaynak][kl["urun"]] -= kl["miktar"]
                    data["depo_stok"][kl["urun"]]["adet"] += kl["miktar"]
                    data["transfer_loglari"].append({"id": len(data["transfer_loglari"])+1, "gün": secilen_gun, "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "kaynak": kaynak, "hedef": "Merkez Depo", "urun": kl["urun"], "miktar": kl["miktar"], "yetkili": teslim_alan, "iptal": False})
                veri_kaydet(data); st.rerun()
    with tab3:
        kaynak = st.selectbox("Çıkış İstasyonu", bar_listesi, key=f"k_b2b_{baslik_kodu}")
        hedef = st.selectbox("Varış İstasyonu", [b for b in bar_listesi if b != kaynak], key=f"h_b2b_{baslik_kodu}")
        teslim_alan = st.text_input("Taşıyan Sorumlu Runner", key=f"y_b2b_{baslik_kodu}")
        secilen_urunler = st.multiselect("Hat Transfer Ürünleri", filtreli_urunler, key=f"multi_b2b_{baslik_kodu}")
        if secilen_urunler:
            sevk_listesi = []
            for u in secilen_urunler:
                g_turu = data["depo_stok"][u]["grup"]
                if g_turu == "Ağır Alkol":
                    c1, c2 = st.columns(2)
                    with c1: s = st.number_input("Şişe", min_value=0, value=None, placeholder="Miktar...", key=f"s_b2b_{u}")
                    with c2: c = st.number_input("CL", min_value=0, value=None, placeholder="CL...", key=f"cl_b2b_{u}")
                    tot = ((s if s is not None else 0) * data["depo_stok"][u]["cl"]) + (c if c is not None else 0)
                    sevk_listesi.append({"urun": u, "miktar": tot, "grup": g_turu})
                else:
                    c1, c2 = st.columns(2)
                    with c1: k = st.number_input("Koli", min_value=0, value=None, placeholder="Koli...", key=f"koli_b2b_{u}")
                    with c2: a = st.number_input("Adet", min_value=0, value=None, placeholder="Adet...", key=f"adet_b2b_{u}")
                    tot = ((k if k is not None else 0) * data["depo_stok"][u]["koli_ici"]) + (a if a is not None else 0)
                    sevk_listesi.append({"urun": u, "miktar": tot, "grup": g_turu})
            if st.button("Transfer Emrini Tetikle", key=f"btn_b2b_exec_{baslik_kodu}"):
                for kl in sevk_listesi:
                    if kl["miktar"] <= 0: continue
                    data["barlar"][kaynak][kl["urun"]] -= kl["miktar"]
                    data["barlar"][hedef][kl["urun"]] = data["barlar"][hedef].get(kl["urun"], 0) + kl["miktar"]
                    data["transfer_loglari"].append({"id": len(data["transfer_loglari"])+1, "gün": secilen_gun, "tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "kaynak": kaynak, "hedef": hedef, "urun": kl["urun"], "miktar": kl["miktar"], "yetkili": teslim_alan, "iptal": False})
                veri_kaydet(data); st.rerun()
    st.write("Geçmiş Lojistik Hareketler")
    if data["transfer_loglari"]:
        t_df = pd.DataFrame(data["transfer_loglari"])
        st.dataframe(t_df, use_container_width=True)

def sayfa_gun_sonu():
    st.title("Gece Sonu Sayım ve Mutabakat")
    if not data["barlar_yeni"]:
        st.warning("Kapatılacak aktif istasyon bulunmuyor."); return
    secilen_gun = st.selectbox("Sayım Günü", GUN_SECIMLERI)
    secilen_bar = st.selectbox("Hesabı Kesilecek İstasyon:", list(data["barlar_yeni"].keys()))
    bar_stoklari = data["barlar"].get(secilen_bar, {})
    if not bar_stoklari:
        st.warning("Bu istasyonda aktif ürün bulunmuyor.")
    else:
        sayim_listesi = [{"Ürün Adı": u, "Depodan Yollanan (Baz Veri)": v, "Gece Kalan Fiziki Sayım": None, "EventPay POS Satış": None} for u, v in bar_stoklari.items() if v > 0]
        duzenlenen_df = st.data_editor(pd.DataFrame(sayim_listesi), disabled=["Ürün Adı", "Depodan Yollanan (Baz Veri)"], use_container_width=True, column_config={"Gece Kalan Fiziki Sayım": st.column_config.NumberColumn("Gece Kalan Fiziki Sayım", min_value=0.0), "EventPay POS Satış": st.column_config.NumberColumn("EventPay POS Satış", min_value=0.0)})
        fis_sayisi = st.number_input("Toplam Fiş Sayısı", min_value=0, step=1, value=0)
        if st.button("Dönem Kapanışını Onayla"):
            girilen_kalanlar = duzenlenen_df.set_index("Ürün Adı")["Gece Kalan Fiziki Sayım"].fillna(0).to_dict()
            pos_verileri = duzenlenen_df.set_index("Ürün Adı")["EventPay POS Satış"].fillna(0).to_dict()
            tuketilen = {urun: bar_stoklari[urun] - girilen_kalanlar.get(urun, 0) for urun in bar_stoklari.keys() if bar_stoklari[urun] > 0}
            rapor = []; tel_lines = []
            toplam_mutabakat_farki = 0
            for u in bar_stoklari.keys():
                if bar_stoklari[u] > 0:
                    grup = data["depo_stok"][u]["grup"]
                    g_satis = round(tuketilen[u] / data["depo_stok"][u]["cl"], 2) if grup == "Ağır Alkol" else round(tuketilen[u], 2)
                    pos_val = pos_verileri.get(u, 0)
                    fark = g_satis - pos_val
                    toplam_mutabakat_farki += fark
                    rapor.append({"Ürün": u, "Fiziki Satış": g_satis, "EventPay POS": pos_val, "Mutabakat Farkı": round(fark, 2)})
                    tel_lines.append(f"Ürün: {u}\n  Tüketim: {g_satis}\n  POS Satış: {pos_val}\n  Fark: {'+' if fark>0 else ''}{round(fark,2)}")
                    data["barlar"][secilen_bar][u] = girilen_kalanlar.get(u, 0)
            st.metric("Toplam Mutabakat Farkı", round(toplam_mutabakat_farki, 2))
            data["rapor_arsivi"].append({"tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "gun": secilen_gun, "bar": secilen_bar, "detaylar": rapor, "toplam_fark": round(toplam_mutabakat_farki, 2), "fis_sayisi": fis_sayisi})
            veri_kaydet(data); st.rerun()

def sayfa_zayiat_free():
    st.title("Fire ve Ağırlama Yönetimi")
    if not data["depo_stok"]:
        st.warning("Sistem katalogları boş."); return
    t1, t2 = st.tabs(["Saha Fire/Zayiat Kaydı", "Protokol / Free İkram Çıkışı"])
    with t1:
        with st.form("z_f_1", clear_on_submit=True):
            gun = st.selectbox("Gün", GUN_SECIMLERI, key="zg")
            loc = st.selectbox("Saha Konumu", ["Merkez Depo"] + list(data["barlar_yeni"].keys()), key="zl")
            ur = st.selectbox("Zayiat Kalemi", list(data["depo_stok"].keys()), key="zu")
            nt = st.text_input("Fire Nedeni", key="zn")
            mq = st.number_input("Zayiat Miktarı", min_value=1, value=None, placeholder="Miktar...", step=1, key="zm")
            if st.form_submit_button("Zayiatı Envanterden Düş"):
                v = mq if mq is not None else 0
                if v > 0:
                    if loc == "Merkez Depo": data["depo_stok"][ur]["adet"] -= v
                    else: data["barlar"][loc][ur] = data["barlar"][loc].get(ur, 0) - v
                    data["zayiatlar"].append({"tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "gun": gun, "konum": loc, "urun": ur, "miktar": v, "not": nt, "depocu_yetkili": st.session_state.active_user_fullname})
                    veri_kaydet(data); st.rerun()
    with t2:
        with st.form("z_f_2", clear_on_submit=True):
            gun = st.selectbox("Gün", GUN_SECIMLERI, key="fg")
            loc = st.selectbox("İkram İstasyonu", ["Merkez Depo"] + list(data["barlar_yeni"].keys()), key="fl")
            isim = st.text_input("Ağırlanan Kişi / Ekip Adı", key="fi")
            ur = st.selectbox("İkram Kalemi", list(data["depo_stok"].keys()), key="fu")
            mq = st.number_input("İkram Miktarı", min_value=1, value=None, placeholder="Miktar...", step=1, key="fm")
            if st.form_submit_button("Free Çıkış Emrini Onayla"):
                v = mq if mq is not None else 0
                if v > 0 and isim.strip():
                    i_isim = isim.strip()
                    if loc == "Merkez Depo": data["depo_stok"][ur]["adet"] -= v
                    else: data["barlar"][loc][ur] = data["barlar"][loc].get(ur, 0) - v
                    data["free_cikislar"].append({"tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "gun": gun, "konum": loc, "isim": i_isim, "urun": ur, "miktar": v, "depocu_yetkili": st.session_state.active_user_fullname})
                    veri_kaydet(data); st.rerun()

def sayfa_kokteyller():
    st.title("Kokteyl Reçete Kataloğu")
    if not data["depo_stok"]: st.warning("Katalog boş."); return
    if data["kokteyl_tanimlari"]: st.dataframe(pd.DataFrame.from_dict(data["kokteyl_tanimlari"], orient='index'), use_container_width=True)
    with st.form("kok_f"):
        k_adi = st.text_input("Kokteyl Adı")
        alkol = st.selectbox("Baz Alkol:", [u for u, d in data["depo_stok"].items() if d["grup"] == "Ağır Alkol"])
        cl = st.number_input("Reçete Alkol Oranı (CL)", min_value=1, value=None, placeholder="CL...", step=1)
        mikser = st.selectbox("Mikser:", [u for u, d in data["depo_stok"].items() if d["grup"] == "Enerji/Mikser"])
        m_adet = st.number_input("Mikser Ölçeği", min_value=1, value=None, placeholder="Adet...", step=1)
        if st.form_submit_button("Formülü Sisteme Kilitle"):
            if k_adi and cl and m_adet:
                data["kokteyl_tanimlari"][k_adi] = {"alkol": alkol, "alkol_cl": cl, "mikser": mikser, "mikser_adet": m_adet}
                veri_kaydet(data); st.rerun()

def sayfa_arsiv():
    st.title("Master Analitik Arşivi")
    gun = st.selectbox("Gün Filtreleme", ["Tüm Günler"] + GUN_SECIMLERI)
    mode = st.selectbox("Rapor Katmanı:", ["Barların Gün Sonu Rapor Arşivi", "Transfer Mutabakat Arşivi", "Sadece Zayiat Raporları", "Sadece Free (İkram) Raporları"])
    if mode == "Barların Gün Sonu Rapor Arşivi" and data["rapor_arsivi"]:
        flt = [r for r in data["rapor_arsivi"] if gun == "Tüm Günler" or r.get("gun") == gun]
        for r in flt:
            with st.expander(f"Gün: [{r.get('gun', 'Belirsiz')}] | İstasyon: {r['bar']} | Tarih: {r['tarih']} | Toplam Fark: {r.get('toplam_fark', 0)} | Fiş Sayısı: {r.get('fis_sayisi', 0)}"):
                st.dataframe(pd.DataFrame(r["detaylar"]), use_container_width=True)
    elif mode == "Transfer Mutabakat Arşivi" and data["transfer_loglari"]:
        df = pd.DataFrame(data["transfer_loglari"])
        if gun != "Tüm Günler": df = df[df["gün"] == gun]
        st.dataframe(df, use_container_width=True)
    elif mode == "Sadece Zayiat Raporları" and data["zayiatlar"]:
        df = pd.DataFrame(data["zayiatlar"])
        if gun != "Tüm Günler": df = df[df["gun"] == gun]
        st.dataframe(df, use_container_width=True)
    elif mode == "Sadece Free (İkram) Raporları" and data["free_cikislar"]:
        df = pd.DataFrame(data["free_cikislar"])
        if gun != "Tüm Günler": df = df[df["gun"] == gun]
        st.dataframe(df, use_container_width=True)

def sayfa_sistem_sifirlama():
    st.title("OS Veritabanı Temizliği")
    st.warning("Bu işlem tüm istasyonları, envanteri, personelleri ve analitik verileri kalıcı olarak siler!")
    c1 = st.checkbox("Tüm verileri kalıcı olarak silmeyi onaylıyorum.")
    txt = st.text_input("Onay kalıbını büyük harflerle yazın (SIFIRLA):")
    if c1 and txt == "SIFIRLA":
        if st.button("OPERASYONU SIFIRLA"):
            st.session_state.data = varsayilan_veri_yapisi(); veri_kaydet(st.session_state.data)
            st.rerun()

def sayfa_kontrolcu_paneli():
    st.title("Kontrolcü İzleme Paneli")
    tab1, tab2, tab3 = st.tabs(["İstasyon Anlık Stokları", "Analitik ve Raporlar", "Merkez Depo Durumu"])
    
    with tab1:
        st.subheader("İstasyonların Sahadaki Güncel Stokları")
        for b in data["barlar"]:
            st.write(f"📍 {b} İstasyonu")
            if data["barlar"][b]:
                st.dataframe(pd.DataFrame([{"Ürün Adı": k, "Adet": v} for k, v in data["barlar"][b].items()]), use_container_width=True)
            else:
                st.info("Bu istasyonda henüz ürün yok.")
                
    with tab2:
        st.subheader("Gün Sonu Mutabakat Raporları")
        if data["rapor_arsivi"]:
            for r in data["rapor_arsivi"]:
                with st.expander(f"Gün: {r.get('gun', '')} | İstasyon: {r['bar']} | Tarih: {r['tarih']} | Toplam Fark: {r.get('toplam_fark', 0)} | Fiş Sayısı: {r.get('fis_sayisi', 0)}"):
                    st.dataframe(pd.DataFrame(r["detaylar"]), use_container_width=True)
        else:
            st.info("Henüz gün sonu raporu bulunmuyor.")
            
        st.subheader("Zayiat Raporları")
        if data["zayiatlar"]: st.dataframe(pd.DataFrame(data["zayiatlar"]), use_container_width=True)
        else: st.info("Zayiat kaydı yok.")
            
        st.subheader("Free (İkram) Çıkışları")
        if data["free_cikislar"]: st.dataframe(pd.DataFrame(data["free_cikislar"]), use_container_width=True)
        else: st.info("İkram kaydı yok.")
            
    with tab3:
        st.subheader("Merkez Depo Anlık Envanteri")
        if data["depo_stok"]:
            depo_df = pd.DataFrame.from_dict(data["depo_stok"], orient='index').reset_index().rename(columns={'index': 'Ürün Adı'})
            st.dataframe(depo_df, use_container_width=True)
        else:
            st.info("Merkez depo şu an boş.")

SAYFALAR_DEPOCU = {
    "Supervisor Listesi": sayfa_supervisor_tanimlama,
    "Bar Tanımlama": sayfa_bar_tanimlama,
    "Depo Stok Giriş Sistemi": sayfa_depo_yonetimi,
    "Depo İşlem Geçmişi": sayfa_depo_gecmisi,
    "Saha Sevkiyat Takip Ekranı": sayfa_depo_takip,
    "Efes Bar Stokları": lambda: jenerik_bar_stogu_goster(get_bar_listesi("Efes"), ["Bira"], "Efes İstasyonları Envanteri"),
    "Redbull Bar Stokları": lambda: jenerik_bar_stogu_goster(get_bar_listesi("Red Bull"), ["Ağır Alkol", "Enerji/Mikser", "Yumuşak Alkol"], "Red Bull İstasyonları Envanteri"),
    "Su Stant Stokları": lambda: jenerik_bar_stogu_goster(get_bar_listesi("Su"), ["Soft Drink", "Diğer"], "Su İstasyonları Envanteri"),
    "Efes Bar Transferleri": lambda: jenerik_transfer_yonetimi_sekmeli(get_bar_listesi("Efes"), ["Bira"], "Efes_İstasyonları"),
    "Redbull Bar Transferleri": lambda: jenerik_transfer_yonetimi_sekmeli(get_bar_listesi("Red Bull"), ["Ağır Alkol", "Enerji/Mikser", "Yumuşak Alkol"], "Red_Bull_İstasyonları"),
    "Su Stant Transferleri": lambda: jenerik_transfer_yonetimi_sekmeli(get_bar_listesi("Su"), ["Soft Drink", "Diğer"], "Su_İstasyonları"),
    "Gece Sayımı ve Eventpay Karşılaştırması": sayfa_gun_sonu,
    "Zayiat ve Free İşleme Paneli": sayfa_zayiat_free,
    "Kokteyl Reçete Paneli": sayfa_kokteyller,
    "Analitik ve Raporlar": sayfa_arsiv,
    "Festival Sonlandırma ve Sistem Sıfırlama": sayfa_sistem_sifirlama
}

SAYFALAR_KONTROLCU = {
    "Kontrolcü Paneli": sayfa_kontrolcu_paneli
}

if st.session_state.user_role == "supervisor":
    sayfa_supervisor_kabul()
elif st.session_state.user_role == "kontrolcu":
    menu = st.sidebar.radio("YÖNETİM MENÜSÜ", list(SAYFALAR_KONTROLCU.keys()))
    SAYFALAR_KONTROLCU[menu]()
else:
    for transfer in data["onay_bekleyen_transferler"]:
        if "hedef_supervisor_username" in transfer and isinstance(transfer["hedef_supervisor_username"], type(getattr)):
            transfer["hedef_supervisor_username"] = "depocu"
    menu = st.sidebar.radio("YÖNETİM MENÜSÜ", list(SAYFALAR_DEPOCU.keys()))
    SAYFALAR_DEPOCU[menu]()
