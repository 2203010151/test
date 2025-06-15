import streamlit as st
import pandas as pd
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# --- KONFIGURASI DASAR & KONEKSI GOOGLE SHEET ---

# Atur Judul dan ikon halaman TEST
st.set_page_config(page_title="Data Tagihan Air", page_icon="💧", layout="wide")

# --- KONSTANTA ---
HARGA_PER_METER_KUBIK = 2500  # Contoh harga: Rp 2.500 per m³
NAMA_GOOGLE_SHEET = "Database Tagihan Air" # Nama file Google Sheet Anda
NAMA_WORKSHEET = "Sheet1" # Nama worksheet di dalam file

# Definisikan Konstanta Nama Kolom untuk perawatan kode yang lebih mudah
COL_KODE_PELANGGAN = 'KODE PELANGGAN'
COL_NAMA = 'NAMA'
COL_KAMPUNG = 'KAMPUNG'
COL_RTRW = 'RT/RW'
COL_METER_LALU = 'JUMLAH METER BULAN LALU'
COL_METER_INI = 'JUMLAH METER BULAN INI'
COL_METER_DIGUNAKAN = 'JUMLAH METER DIGUNAKAN BULAN INI'
COL_TAGIHAN_BULAN_INI = 'TAGIHAN YANG HARUS DI BAYAR BULAN INI'
COL_SUDAH_BAYAR = 'TAGIHAN YANG SUDAH DI BAYAR BULAN INI'
COL_SISA_TAGIHAN = 'SISA TAGIHAN BULAN INI'
COL_TUNGGAKAN_LALU = 'TUNGGAKAN DARI BULAN LALU'
COL_TOTAL_TAGIHAN = 'TOTAL TAGIHAN (TERMASUK TUNGGAKAN)'
COL_TANGGAL_INPUT = 'TANGGAL INPUT'

# Urutan kolom sesuai dengan di Google Sheet (PENTING untuk append_row/update)
COLUMN_ORDER = [
    COL_KODE_PELANGGAN, COL_NAMA, COL_KAMPUNG, COL_RTRW,
    COL_METER_LALU, COL_METER_INI, COL_METER_DIGUNAKAN,
    COL_TAGIHAN_BULAN_INI, COL_SUDAH_BAYAR, COL_SISA_TAGIHAN,
    COL_TUNGGAKAN_LALU, COL_TOTAL_TAGIHAN, COL_TANGGAL_INPUT
]


# --- FUNGSI-FUNGSI ---

# Fungsi untuk koneksi ke Google Sheets menggunakan Streamlit Secrets
@st.cache_resource
def connect_to_gsheet():
    """Menghubungkan ke Google Sheet dan mengembalikan objek worksheet."""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["google_cloud"], scopes=scopes
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open(NAMA_GOOGLE_SHEET)
        worksheet = spreadsheet.worksheet(NAMA_WORKSHEET)
        return worksheet
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets. Pastikan API telah diaktifkan dan Sheet sudah di-share. Error: {e}")
        return None

# Fungsi untuk memuat data dari worksheet
@st.cache_data(ttl=60) # Cache data selama 60 detik
def load_data(_worksheet):
    """Memuat data dari worksheet, membersihkan, dan mengonversi tipe data."""
    if not _worksheet:
        return pd.DataFrame()
    try:
        df = get_as_dataframe(_worksheet, parse_dates=True, header=0, usecols=list(range(len(COLUMN_ORDER))))
        df.columns = COLUMN_ORDER # Pastikan nama kolom sesuai urutan
        df.dropna(how='all', inplace=True)
        
        numeric_cols = [
            COL_METER_LALU, COL_METER_INI, COL_SUDAH_BAYAR, COL_TUNGGAKAN_LALU,
            COL_TAGIHAN_BULAN_INI, COL_SISA_TAGIHAN, COL_TOTAL_TAGIHAN
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Pastikan kolom tanggal di-handle dengan baik
        if COL_TANGGAL_INPUT in df.columns:
            df[COL_TANGGAL_INPUT] = pd.to_datetime(df[COL_TANGGAL_INPUT], errors='coerce')

        # Pastikan kode pelanggan selalu uppercase
        if COL_KODE_PELANGGAN in df.columns:
            df[COL_KODE_PELANGGAN] = df[COL_KODE_PELANGGAN].astype(str).str.upper()

        return df
    except Exception as e:
        st.error(f"Gagal memuat data dari worksheet. Error: {e}")
        return pd.DataFrame()

# Panggil fungsi koneksi dan muat data
worksheet = connect_to_gsheet()
df = load_data(worksheet)

# --- TAMPILAN APLIKASI STREAMLIT ---

st.title("💧 Aplikasi Pendataan & Pembayaran Air Bersih")
st.markdown("---")

# Membuat tab untuk memisahkan fungsionalitas
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Data Pelanggan", "📝 Input & Pembayaran (Update)", "👤 Tambah Pelanggan Baru"])

with tab1:
    st.header("Dashboard Informasi")
    if not df.empty:
        # Ambil data entri terakhir untuk setiap pelanggan untuk perhitungan akurat
        last_entries = df.loc[df.groupby(COL_KODE_PELANGGAN)[COL_TANGGAL_INPUT].idxmax()]
        
        total_pelanggan = last_entries[COL_KODE_PELANGGAN].nunique()
        total_sisa_tagihan = last_entries[COL_SISA_TAGIHAN].sum()

        col1, col2 = st.columns(2)
        col1.metric("Jumlah Pelanggan Aktif", f"{total_pelanggan} orang")
        col2.metric("Estimasi Total Sisa Tagihan Pelanggan", f"Rp {total_sisa_tagihan:,.0f}")

    st.header("Data Seluruh Pelanggan")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    if worksheet and not df.empty:
        # Format tampilan mata uang pada dataframe
        st.dataframe(df.style.format({
            COL_TAGIHAN_BULAN_INI: 'Rp {:,.0f}',
            COL_SUDAH_BAYAR: 'Rp {:,.0f}',
            COL_SISA_TAGIHAN: 'Rp {:,.0f}',
            COL_TUNGGAKAN_LALU: 'Rp {:,.0f}',
            COL_TOTAL_TAGIHAN: 'Rp {:,.0f}',
            COL_TANGGAL_INPUT: '{:%Y-%m-%d %H:%M:%S}'
        }, na_rep='-'))
    else:
        st.warning("Gagal memuat data atau data masih kosong. Periksa koneksi dan konfigurasi, atau tambahkan pelanggan baru.")


with tab2:
    st.header("Input Pembayaran & Meteran Bulan Ini")
    st.warning(
        "⚠️ **Mode Update:** Input baru akan **mengganti** data bulan lalu milik pelanggan. "
        "Untuk mencatat riwayat per bulan, diperlukan logika `append` (menambah baris baru)."
    )

    if not df.empty:
        daftar_pelanggan = sorted(df[COL_NAMA].unique().tolist())
        
        nama_pelanggan_terpilih = st.selectbox(
            "Pilih Nama Pelanggan", 
            options=daftar_pelanggan, 
            index=None, 
            placeholder="Ketik atau pilih nama..."
        )

        if nama_pelanggan_terpilih:
            kode_pelanggan = df[df[COL_NAMA] == nama_pelanggan_terpilih][COL_KODE_PELANGGAN].iloc[0]
            
            try:
                # Ambil baris data terakhir milik pelanggan
                data_terakhir = df[df[COL_KODE_PELANGGAN] == kode_pelanggan].sort_values(by=COL_TANGGAL_INPUT, ascending=False).iloc[0]
                # Dapatkan indeks baris di GSheet untuk diupdate (+2 karena 1-based index dan 1 baris header)
                row_index_to_update = int(data_terakhir.name) + 2 
            except IndexError:
                st.error(f"Tidak dapat menemukan data untuk pelanggan '{nama_pelanggan_terpilih}'.")
                st.stop()

            st.info(f"Mengupdate data untuk: **{nama_pelanggan_terpilih}** (Kode: {kode_pelanggan})")
            
            # --- PERUBAHAN STRUKTUR ---
            # 1. Tampilkan data referensi di luar form
            st.subheader("Data Bulan Lalu (Sebagai Referensi)")
            
            # Ambil semua data referensi dari data_terakhir
            meter_lalu_untuk_hitung = data_terakhir[COL_METER_INI]
            tunggakan_dibawa = data_terakhir[COL_SISA_TAGIHAN]
            total_tagihan_lalu = data_terakhir[COL_TOTAL_TAGIHAN]
            
            # Tampilkan dalam kolom
            ref_col1, ref_col2, ref_col3 = st.columns(3)
            ref_col1.metric("Jumlah Meter Bulan Lalu (m³)", f"{meter_lalu_untuk_hitung:,.0f}")
            ref_col2.metric("Tunggakan dari Bulan Lalu", f"Rp {tunggakan_dibawa:,.0f}")
            ref_col3.metric("Total Tagihan Lalu (Ref)", f"Rp {total_tagihan_lalu:,.0f}")
            
            st.markdown("---")

            # 2. Form hanya untuk input data baru
            with st.form("form_pembayaran_update"):
                st.write("**Input Data Baru**")
                in_col1, in_col2 = st.columns(2)
                
                meter_ini = in_col1.number_input("Input Jumlah Meter Bulan Ini (m³)", min_value=float(meter_lalu_untuk_hitung), step=1.0)
                bayar_bulan_ini = in_col2.number_input("Jumlah yang Dibayar Bulan Ini (Rp)", min_value=0, step=1000)
                
                submitted = st.form_submit_button("Update & Hitung Ulang Tagihan")

                if submitted:
                    if meter_ini < meter_lalu_untuk_hitung:
                        st.error("Jumlah meter bulan ini tidak boleh lebih kecil dari meteran bulan lalu.")
                    else:
                        # --- PERHITUNGAN ---
                        pemakaian_kubik = meter_ini - meter_lalu_untuk_hitung
                        tagihan_bulan_ini = pemakaian_kubik * HARGA_PER_METER_KUBIK
                        total_tagihan_sekarang = tagihan_bulan_ini + tunggakan_dibawa
                        sisa_tagihan_sekarang = total_tagihan_sekarang - bayar_bulan_ini
                        
                        # --- PERSIAPAN DATA UNTUK DISIMPAN ---
                        data_untuk_update = {
                            COL_KODE_PELANGGAN: kode_pelanggan,
                            COL_NAMA: nama_pelanggan_terpilih,
                            COL_KAMPUNG: data_terakhir[COL_KAMPUNG],
                            COL_RTRW: data_terakhir[COL_RTRW],
                            COL_METER_LALU: meter_lalu_untuk_hitung,
                            COL_METER_INI: meter_ini,
                            COL_METER_DIGUNAKAN: pemakaian_kubik,
                            COL_TAGIHAN_BULAN_INI: tagihan_bulan_ini,
                            COL_SUDAH_BAYAR: bayar_bulan_ini,
                            COL_SISA_TAGIHAN: sisa_tagihan_sekarang,
                            COL_TUNGGAKAN_LALU: tunggakan_dibawa,
                            COL_TOTAL_TAGIHAN: total_tagihan_sekarang,
                            COL_TANGGAL_INPUT: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        # --- PERUBAHAN TAMPILAN HASIL ---
                        st.success("Perhitungan Ulang Berhasil!")
                        st.subheader("Hasil Perhitungan Tagihan Bulan Ini")
                        
                        res_col1, res_col2 = st.columns(2)
                        res_col1.metric("Pemakaian Bulan Ini", f"{pemakaian_kubik:,.0f} m³")
                        res_col1.metric("Tagihan Murni Bulan Ini", f"Rp {tagihan_bulan_ini:,.0f}")
                        res_col2.metric("TOTAL TAGIHAN BULAN INI", f"Rp {total_tagihan_sekarang:,.0f}")
                        res_col2.metric("SISA TAGIHAN / TUNGGAKAN BARU", f"Rp {sisa_tagihan_sekarang:,.0f}", delta_color="inverse")
                        
                        st.info(f"Jumlah Dibayar: Rp {bayar_bulan_ini:,.0f}")
                        st.markdown("---")


                        # --- PROSES PENYIMPANAN DATA ---
                        try:
                            st.write("Menyimpan data ke Google Sheets...")
                            update_values = [data_untuk_update[col] for col in COLUMN_ORDER]
                            worksheet.update(f'A{row_index_to_update}', [update_values], value_input_option='USER_ENTERED')
                            
                            st.success(f"✅ Data untuk '{nama_pelanggan_terpilih}' berhasil diperbarui!")
                            st.balloons()
                            
                            # Tombol untuk me-refresh halaman secara manual setelah update
                            if st.button("Selesai & Muat Ulang Data"):
                                st.cache_data.clear()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Gagal memperbarui data ke Google Sheets. Error: {e}")
    else:
        st.warning("Belum ada data pelanggan. Silakan tambahkan pelanggan baru di tab 'Tambah Pelanggan Baru'.")

with tab3:
    st.header("Form Pendaftaran Pelanggan Baru")
    with st.form("form_pelanggan_baru", clear_on_submit=True):
        kode_pelanggan_baru = st.text_input("Kode Pelanggan (Contoh: A001)")
        nama_baru = st.text_input("Nama Lengkap")
        kampung_baru = st.text_input("Kampung")
        rtrw_baru = st.text_input("RT/RW (Contoh: 001/002)")
        meter_awal = st.number_input("Angka Awal di Meteran (m³)", min_value=0.0, step=1.0)
        
        submitted_baru = st.form_submit_button("Daftarkan Pelanggan")

        if submitted_baru:
            kode_pelanggan_baru_upper = kode_pelanggan_baru.strip().upper()

            if not all([kode_pelanggan_baru_upper, nama_baru, kampung_baru, rtrw_baru]):
                st.error("Semua field harus diisi.")
            elif not df.empty and kode_pelanggan_baru_upper in df[COL_KODE_PELANGGAN].values:
                st.error("Kode Pelanggan sudah ada. Gunakan kode unik.")
            else:
                data_pelanggan_baru = {
                    COL_KODE_PELANGGAN: kode_pelanggan_baru_upper,
                    COL_NAMA: nama_baru.strip(),
                    COL_KAMPUNG: kampung_baru.strip(),
                    COL_RTRW: rtrw_baru.strip(),
                    COL_METER_LALU: 0,
                    COL_METER_INI: meter_awal,
                    COL_METER_DIGUNAKAN: 0,
                    COL_TAGIHAN_BULAN_INI: 0,
                    COL_SUDAH_BAYAR: 0,
                    COL_SISA_TAGIHAN: 0,
                    COL_TUNGGAKAN_LALU: 0,
                    COL_TOTAL_TAGIHAN: 0,
                    COL_TANGGAL_INPUT: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                try:
                    new_customer_values = [data_pelanggan_baru[col] for col in COLUMN_ORDER]
                    worksheet.append_row(new_customer_values, value_input_option='USER_ENTERED')
                    st.success(f"✅ Pelanggan baru '{nama_baru}' dengan kode '{kode_pelanggan_baru_upper}' berhasil ditambahkan!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan data pelanggan baru ke Google Sheets. Error: {e}")
