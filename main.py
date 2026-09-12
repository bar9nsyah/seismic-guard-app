import threading
import time
import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

URL_AUTOGEMPA = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
URL_CUACA_JABAR = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=-6.9175&longitude=107.6191&current=temperature_2m,relative_humidity_2m,weather_code&timezone=Asia%2FJakarta"
)


def get_weather_desc(code):
    if code in [0]:
        return "Cerah"
    elif code in [1, 2, 3]:
        return "Cerah Berawan"
    elif code in [45, 48]:
        return "Berkabut"
    elif code in [51, 53, 55, 61, 63, 65]:
        return "Hujan Ringan/Sedang"
    elif code in [80, 81, 82]:
        return "Hujan Deras"
    elif code in [95, 96, 99]:
        return "Hujan Petir"
    return "Berawan"


class StyledCard(BoxLayout):
    def __init__(self, bg_color=(0.08, 0.12, 0.2, 1), radius=14, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius
        self.bg_color = bg_color
        with self.canvas.before:
            self.card_color = Color(*self.bg_color)
            self.rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class SeismicGuardApp(App):
    def build(self):
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_event_id = None
        self.alarm_sound = None

        root = BoxLayout(orientation="vertical", padding=12, spacing=10)
        with root.canvas.before:
            Color(0.04, 0.06, 0.1, 1)  # Latar belakang deep navy
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *args: setattr(self.bg_rect, "pos", root.pos),
            size=lambda *args: setattr(self.bg_rect, "size", root.size),
        )

        # 1. Header & Widget Cuaca
        weather_card = StyledCard(
            bg_color=(0.07, 0.15, 0.25, 0.9),
            orientation="horizontal",
            size_hint_y=None,
            height=70,
            padding=[14, 8],
            spacing=10,
        )

        title_box = BoxLayout(orientation="vertical")
        lbl_app_title = Label(
            text="SEISMIC GUARD v2.1",
            font_size="16sp",
            bold=True,
            color=(0.2, 0.8, 1, 1),
            halign="left",
            valign="middle",
        )
        lbl_app_title.bind(size=lbl_app_title.setter("text_size"))

        lbl_sub = Label(
            text="Radar Zona Jawa Barat & Selat Sunda",
            font_size="11sp",
            color=(0.6, 0.7, 0.8, 1),
            halign="left",
            valign="middle",
        )
        lbl_sub.bind(size=lbl_sub.setter("text_size"))
        title_box.add_widget(lbl_app_title)
        title_box.add_widget(lbl_sub)

        weather_info_box = BoxLayout(
            orientation="vertical", size_hint_x=None, width=130
        )
        self.lbl_weather_temp = Label(
            text="--°C",
            font_size="15sp",
            bold=True,
            color=(1, 0.8, 0.2, 1),
            halign="right",
            valign="middle",
        )
        self.lbl_weather_temp.bind(size=self.lbl_weather_temp.setter("text_size"))

        self.lbl_weather_status = Label(
            text="Memuat Cuaca...",
            font_size="10sp",
            color=(0.7, 0.8, 0.9, 1),
            halign="right",
            valign="middle",
        )
        self.lbl_weather_status.bind(
            size=self.lbl_weather_status.setter("text_size")
        )

        weather_info_box.add_widget(self.lbl_weather_temp)
        weather_info_box.add_widget(self.lbl_weather_status)

        weather_card.add_widget(title_box)
        weather_card.add_widget(weather_info_box)
        root.add_widget(weather_card)

        # Scroll area untuk informasi utama & peta
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content_box = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=10
        )
        content_box.bind(minimum_height=content_box.setter("height"))

        # 2. Status Sistem
        self.status_card = StyledCard(
            bg_color=(0.12, 0.14, 0.18, 1),
            size_hint_y=None,
            height=40,
            padding=[10, 5],
        )
        self.lbl_status = Label(
            text="Status Sistem: SIAGA (OFFLINE)",
            bold=True,
            font_size="12sp",
            color=(1, 0.5, 0.2, 1),
        )
        self.status_card.add_widget(self.lbl_status)
        content_box.add_widget(self.status_card)

        # 3. Kartu Informasi Gempa Utama
        quake_card = StyledCard(
            bg_color=(0.09, 0.13, 0.22, 1),
            orientation="vertical",
            size_hint_y=None,
            height=190,
            padding=12,
            spacing=4,
        )

        self.lbl_mag = Label(
            text="-- SR",
            font_size="38sp",
            bold=True,
            color=(1, 0.75, 0.1, 1),
            size_hint_y=None,
            height=50,
        )
        quake_card.add_widget(self.lbl_mag)

        self.lbl_wilayah = Label(
            text="Pusat: Menunggu sinkronisasi radar...",
            font_size="13sp",
            bold=True,
            color=(1, 1, 1, 1),
            halign="center",
        )
        self.lbl_wilayah.bind(size=self.lbl_wilayah.setter("text_size"))
        quake_card.add_widget(self.lbl_wilayah)

        self.lbl_waktu = Label(
            text="Waktu Kejadian: -",
            font_size="11sp",
            color=(0.7, 0.75, 0.85, 1),
        )
        self.lbl_kedalaman = Label(
            text="Kedalaman: -",
            font_size="11sp",
            color=(0.7, 0.75, 0.85, 1),
        )
        self.lbl_koordinat = Label(
            text="Koordinat: -",
            font_size="11sp",
            color=(0.3, 0.7, 0.9, 1),
        )

        quake_card.add_widget(self.lbl_waktu)
        quake_card.add_widget(self.lbl_kedalaman)
        quake_card.add_widget(self.lbl_koordinat)
        content_box.add_widget(quake_card)

        # 4. Peta Shakemap BMKG
        shakemap_card = StyledCard(
            bg_color=(0.06, 0.1, 0.16, 1),
            orientation="vertical",
            size_hint_y=None,
            height=280,
            padding=8,
            spacing=6,
        )

        lbl_map_header = Label(
            text="PETA GUNCANGAN BMKG (SHAKEMAP)",
            font_size="11sp",
            bold=True,
            color=(0.5, 0.7, 0.9, 1),
            size_hint_y=None,
            height=20,
        )
        shakemap_card.add_widget(lbl_map_header)

        self.img_shakemap = AsyncImage(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            size_hint_y=None,
            height=240,
        )
        shakemap_card.add_widget(self.img_shakemap)
        content_box.add_widget(shakemap_card)

        scroll.add_widget(content_box)
        root.add_widget(scroll)

        # 5. Tombol Kontrol Bawah
        btn_box = BoxLayout(
            orientation="vertical", size_hint_y=None, height=95, spacing=6
        )

        self.btn_simulasi = Button(
            text="SIMULASI ALARM DARURAT (TES)",
            background_normal="",
            background_color=(0.2, 0.25, 0.35, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="12sp",
        )
        self.btn_simulasi.bind(on_release=self.tes_alarm)

        self.btn_toggle = Button(
            text="AKTIFKAN RADAR PEMANTAU",
            background_normal="",
            background_color=(0.0, 0.6, 0.85, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
        )
        self.btn_toggle.bind(on_release=self.toggle_monitoring)

        btn_box.add_widget(self.btn_simulasi)
        btn_box.add_widget(self.btn_toggle)
        root.add_widget(btn_box)

        # Memulai pengambilan data cuaca berkala
        threading.Thread(target=self.fetch_weather, daemon=True).start()

        return root

    def fetch_weather(self):
        try:
            r = requests.get(URL_CUACA_JABAR, timeout=6)
            if r.status_code == 200:
                data = r.json().get("current", {})
                temp = data.get("temperature_2m", "--")
                code = data.get("weather_code", 0)
                desc = get_weather_desc(code)
                Clock.schedule_once(
                    lambda dt: self.update_weather_ui(f"{temp}°C", desc)
                )
        except Exception:
            Clock.schedule_once(
                lambda dt: self.update_weather_ui("--°C", "Cuaca Terputus")
            )

    def update_weather_ui(self, temp_str, desc_str):
        self.lbl_weather_temp.text = temp_str
        self.lbl_weather_status.text = desc_str

    def toggle_monitoring(self, instance):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.btn_toggle.text = "NONAKTIFKAN RADAR"
            self.btn_toggle.background_color = (0.8, 0.2, 0.2, 1)
            self.lbl_status.text = "Status Sistem: RADAR AKTIF (MEMANTAU)"
            self.lbl_status.color = (0.2, 1.0, 0.4, 1)

            self.monitor_thread = threading.Thread(
                target=self.monitoring_worker, daemon=True
            )
            self.monitor_thread.start()
        else:
            self.is_monitoring = False
            self.btn_toggle.text = "AKTIFKAN RADAR PEMANTAU"
            self.btn_toggle.background_color = (0.0, 0.6, 0.85, 1)
            self.lbl_status.text = "Status Sistem: SIAGA (OFFLINE)"
            self.lbl_status.color = (1.0, 0.5, 0.2, 1)

    def monitoring_worker(self):
        while self.is_monitoring:
            try:
                r = requests.get(URL_AUTOGEMPA, timeout=6)
                if r.status_code == 200:
                    data = r.json().get("Infogempa", {}).get("gempa", {})
                    mag = float(str(data.get("Magnitude", "0")).replace(",", "."))
                    wilayah = data.get("Wilayah", "")
                    waktu = f"{data.get('Tanggal', '')} | {data.get('Jam', '')}"
                    kedalaman = data.get("Kedalaman", "")
                    koordinat = data.get("Coordinates", "")
                    shakemap = data.get("Shakemap", "")
                    event_id = f"{data.get('DateTime', '')}_{mag}"

                    Clock.schedule_once(
                        lambda dt: self.update_quake_ui(
                            mag, wilayah, waktu, kedalaman, koordinat, shakemap
                        )
                    )

                    if self.last_event_id is None:
                        self.last_event_id = event_id
                    elif self.last_event_id != event_id:
                        self.last_event_id = event_id
                        self.bunyikan_alarm()
            except Exception:
                pass

            for _ in range(20):
                if not self.is_monitoring:
                    break
                time.sleep(1)

    def update_quake_ui(self, mag, wilayah, waktu, kedalaman, koordinat, shakemap):
        self.lbl_mag.text = f"{mag} SR"
        if mag >= 5.0:
            self.lbl_mag.color = (1.0, 0.2, 0.2, 1)  # Merah
        elif mag >= 3.5:
            self.lbl_mag.color = (1.0, 0.75, 0.1, 1)  # Kuning
        else:
            self.lbl_mag.color = (0.2, 0.9, 0.4, 1)  # Hijau

        self.lbl_wilayah.text = f"Pusat: {wilayah}"
        self.lbl_waktu.text = f"Waktu: {waktu}"
        self.lbl_kedalaman.text = f"Kedalaman: {kedalaman}"
        self.lbl_koordinat.text = f"Koordinat: {koordinat}"

        if shakemap:
            self.img_shakemap.source = (
                f"https://data.bmkg.go.id/DataMKG/TEWS/{shakemap}"
            )
            self.img_shakemap.reload()

    def tes_alarm(self, instance):
        self.bunyikan_alarm()

    def bunyikan_alarm(self):
        # Placeholder integrasi audio jika ada file alarm.wav di folder aplikasi
        try:
            sound = SoundLoader.load("alarm.wav")
            if sound:
                sound.play()
        except Exception:
            pass

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    SeismicGuardApp().run()
                    
