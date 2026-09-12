import threading
import time
import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

Window.clearcolor = (0.05, 0.07, 0.11, 1.0)

URL_AUTOGEMPA = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
URL_DIRASAKAN = "https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json"

KEYWORDS_TARGET = [
    "jawa barat", "jabar", "selat sunda", "banten", "sumur", "lebak", "pandeglang",
    "sukabumi", "cianjur", "garut", "tasikmalaya", "pangandaran", "laut jawa",
    "samudra hindia selatan jawa", "selatan jawa barat", "bandung", "bogor",
    "pelabuhanratu", "muarabinuangeun", "bayah", "ujung kulon", "serang", "cilegon"
]

class CardBox(BoxLayout):
    def __init__(self, bg_color=(0.10, 0.13, 0.19, 1.0), **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        with self.canvas.before:
            self.rect_color = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class SeismicGuardApp(App):
    def build(self):
        self.title = "SEISMIC GUARD | JAWA BARAT & SUNDA"
        self.is_monitoring = False
        self.last_event_id = None

        root = BoxLayout(orientation='vertical', padding=16, spacing=12)

        header = CardBox(
            bg_color=(0.08, 0.11, 0.17, 1.0),
            orientation='vertical',
            size_hint=(1, None),
            height=85,
            padding=8
        )
        header.add_widget(Label(
            text="[b]SEISMIC GUARD v2.1[/b]",
            markup=True,
            font_size="19sp",
            color=(0.2, 0.85, 1.0, 1.0)
        ))
        header.add_widget(Label(
            text="Zona: Jabar • Banten • Selat Sunda • Laut Selatan (1.1 - 6.9 SR)",
            font_size="11sp",
            color=(0.6, 0.7, 0.8, 1.0)
        ))
        root.add_widget(header)

        status_card = CardBox(
            bg_color=(0.08, 0.10, 0.15, 1.0),
            size_hint=(1, None),
            height=42,
            padding=[12, 0]
        )
        self.lbl_status = Label(
            text="Status Sistem: [b][color=ffaa00]SIAGA (OFFLINE)[/color][/b]",
            markup=True,
            font_size="12sp",
            halign="left",
            valign="middle"
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        status_card.add_widget(self.lbl_status)
        root.add_widget(status_card)

        scroll = ScrollView(size_hint=(1, 1))
        content_box = CardBox(
            bg_color=(0.10, 0.14, 0.22, 1.0),
            orientation='vertical',
            padding=16,
            spacing=10,
            size_hint_y=None
        )
        content_box.bind(minimum_height=content_box.setter('height'))

        self.lbl_mag = Label(
            text="-- SR",
            font_size="44sp",
            bold=True,
            color=(1.0, 0.8, 0.2, 1.0),
            size_hint_y=None,
            height=58
        )
        self.lbl_wilayah = Label(
            text="Pusat: Menunggu pemindaian...",
            font_size="13sp",
            bold=True,
            color=(1.0, 1.0, 1.0, 1.0),
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=50
        )
        self.lbl_wilayah.bind(width=lambda s, w: setattr(s, 'text_size', (w, None)))

        self.lbl_waktu = Label(
            text="Waktu Kejadian: -",
            font_size="12sp",
            color=(0.8, 0.8, 0.9, 1.0),
            size_hint_y=None,
            height=24
        )
        self.lbl_kedalaman = Label(
            text="Kedalaman: -",
            font_size="12sp",
            color=(0.8, 0.8, 0.9, 1.0),
            size_hint_y=None,
            height=24
        )
        self.lbl_koordinat = Label(
            text="Koordinat: -",
            font_size="12sp",
            color=(0.4, 0.8, 1.0, 1.0),
            size_hint_y=None,
            height=24
        )

        content_box.add_widget(self.lbl_mag)
        content_box.add_widget(self.lbl_wilayah)
        content_box.add_widget(self.lbl_waktu)
        content_box.add_widget(self.lbl_kedalaman)
        content_box.add_widget(self.lbl_koordinat)
        scroll.add_widget(content_box)
        root.add_widget(scroll)

        btn_test = Button(
            text="SIMULASI ALARM DARURAT (TES)",
            size_hint=(1, None),
            height=44,
            font_size="12sp",
            bold=True,
            background_normal="",
            background_color=(0.28, 0.33, 0.42, 1.0)
        )
        btn_test.bind(on_press=self.simulasi_gempa)
        root.add_widget(btn_test)

        self.btn_toggle = Button(
            text="AKTIFKAN RADAR PEMANTAU",
            size_hint=(1, None),
            height=50,
            font_size="14sp",
            bold=True,
            background_normal="",
            background_color=(0.0, 0.65, 0.85, 1.0)
        )
        self.btn_toggle.bind(on_press=self.toggle_monitoring)
        root.add_widget(self.btn_toggle)

        return root

    def toggle_monitoring(self, instance):
        if not self.is_monitoring:
            self.is_monitoring = True
            self.btn_toggle.text = "HENTIKAN PEMANTAU"
            self.btn_toggle.background_color = (0.85, 0.25, 0.25, 1.0)
            self.lbl_status.text = "Status Sistem: [b][color=00ff88]RADAR AKTIF (TERHUBUNG BMKG)[/color][/b]"
            threading.Thread(target=self.monitoring_worker, daemon=True).start()
        else:
            self.is_monitoring = False
            self.btn_toggle.text = "AKTIFKAN RADAR PEMANTAU"
            self.btn_toggle.background_color = (0.0, 0.65, 0.85, 1.0)
            self.lbl_status.text = "Status Sistem: [b][color=ffaa00]SIAGA (OFFLINE)[/color][/b]"

    def simulasi_gempa(self, instance):
        self.update_ui(
            mag=5.2,
            wilayah="Pusat: Laut 65 km Barat Daya Sumur-Banten",
            waktu="Simulasi Sistem (Darurat)",
            kedalaman="10 km",
            lat=-6.85,
            lon=105.20
        )
        self.bunyikan_alarm()

    def bunyikan_alarm(self):
        try:
            sound = SoundLoader.load("alarm.mp3")
            if sound:
                sound.play()
        except Exception:
            pass

    def is_target_sector(self, lat, lon, wilayah):
        if -8.9 <= lat <= -5.5 and 105.0 <= lon <= 109.2:
            return True
        w_low = wilayah.lower()
        return any(kw in w_low for kw in KEYWORDS_TARGET)

    def update_ui(self, mag, wilayah, waktu, kedalaman, lat, lon):
        self.lbl_mag.text = f"{mag} SR"
        self.lbl_mag.color = (1.0, 0.2, 0.2, 1.0) if mag >= 5.0 else (1.0, 0.8, 0.2, 1.0)
        self.lbl_wilayah.text = wilayah
        self.lbl_waktu.text = f"Waktu Kejadian: {waktu}"
        self.lbl_kedalaman.text = f"Kedalaman: {kedalaman}"
        self.lbl_koordinat.text = f"Koordinat: Lat {lat}° | Lon {lon}°"

    def monitoring_worker(self):
        while self.is_monitoring:
            try:
                events = []
                r1 = requests.get(URL_AUTOGEMPA, timeout=6)
                if r1.status_code == 200:
                    events.append(r1.json()['Infogempa']['gempa'])

                r2 = requests.get(URL_DIRASAKAN, timeout=6)
                if r2.status_code == 200:
                    data_r = r2.json()['Infogempa']['gempa']
                    if isinstance(data_r, list):
                        events.extend(data_r[:5])
                    elif isinstance(data_r, dict):
                        events.append(data_r)

                for item in events:
                    event_id = item.get('DateTime') or (item.get('Tanggal', '') + "@" + item.get('Jam', ''))

                    try:
                        mag = float(str(item.get('Magnitude', '0')).replace(',', '.'))
                    except ValueError:
                        continue

                    raw_coords = item.get('Coordinates', '')
                    if not raw_coords and 'Lintang' in item and 'Bujur' in item:
                        lat_val = float(str(item['Lintang']).replace(' LS', '').replace(' LU', '').replace(',', '.'))
                        if 'LS' in str(item['Lintang']):
                            lat_val = -abs(lat_val)
                        lon_val = float(str(item['Bujur']).replace(' BT', '').replace(',', '.'))
                    elif raw_coords:
                        parts = [float(x.strip()) for x in raw_coords.split(',')]
                        lat_val, lon_val = parts[0], parts[1]
                    else:
                        continue

                    wilayah = item.get('Wilayah', '')
                    kedalaman = item.get('Kedalaman', '-')
                    waktu = f"{item.get('Tanggal')} | {item.get('Jam')}"

                    if self.is_target_sector(lat_val, lon_val, wilayah) and (1.1 <= mag <= 6.9):
                        Clock.schedule_once(
                            lambda dt, m=mag, w=wilayah, t=waktu, k=kedalaman, la=lat_val, lo=lon_val: 
                            self.update_ui(m, w, t, k, la, lo)
                        )
                        if event_id != self.last_event_id:
                            self.last_event_id = event_id
                            self.bunyikan_alarm()
                        break
            except Exception:
                pass

            for _ in range(20):
                if not self.is_monitoring:
                    break
                time.sleep(1)

    def on_pause(self):
        return True

    def on_resume(self):
        pass

if __name__ == '__main__':
    SeismicGuardApp().run()
