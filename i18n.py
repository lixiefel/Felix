"""
i18n.py — Translation strings for MarginLab.
Two languages: 'en' (English) and 'id' (Bahasa Indonesia).

Usage:
    from i18n import t
    t("hero_h1", lang)  # returns the translated string

Strings missing in a non-English language fall back to the English version.
"""

STRINGS = {
    # ── Landing ──────────────────────────────────────────────────────────────
    "nav_brand_tagline":     {"en": "Pricing Lab",                                       "id": "Lab Penetapan Harga"},
    "nav_built_for":         {"en": "Built for café operators",                          "id": "Dibuat untuk pemilik kafé"},
    "hero_eyebrow":          {"en": "A free pricing audit · No login",                   "id": "Audit harga gratis · Tanpa login"},
    "hero_h1_part1":         {"en": "Pricing your menu, with the ",                      "id": "Tetapkan harga menu Anda dengan "},
    "hero_h1_accent":        {"en": "rigor",                                             "id": "ketelitian"},
    "hero_h1_part2":         {"en": " it deserves.",                                     "id": " yang layak."},
    "hero_sub":              {"en": "A 5-minute audit grounded in Lerner-optimal economics, menu-engineering theory, and confidence-weighted shrinkage. You enter your menu — we email you a PDF report with item-by-item recommendations.",
                              "id": "Audit lima menit berbasis ekonomi Lerner-optimal, teori menu-engineering, dan shrinkage berbobot keyakinan. Anda mengisi menu — kami mengirim laporan PDF dengan rekomendasi per-item ke email Anda."},
    "hero_bullet_1":         {"en": "Free",                                              "id": "Gratis"},
    "hero_bullet_2":         {"en": "No login required",                                 "id": "Tanpa login"},
    "hero_bullet_3":         {"en": "Report in your inbox",                              "id": "Laporan dikirim ke email"},
    "hero_bullet_4":         {"en": "~30 seconds to run",                                "id": "~30 detik untuk dijalankan"},
    "cta_start":             {"en": "Start your free audit",                             "id": "Mulai audit gratis"},
    "cta_get":               {"en": "Get my free audit",                                 "id": "Dapatkan audit gratis saya"},

    "how_label":             {"en": "How it works",                                      "id": "Cara kerja"},
    "how_1_title":           {"en": "Enter your menu",                                   "id": "Isi menu Anda"},
    "how_1_body":            {"en": "Items, costs, current prices, monthly units. Takes about 5 minutes for a typical café.",
                              "id": "Item, biaya, harga saat ini, jumlah terjual per bulan. Sekitar lima menit untuk kafé biasa."},
    "how_2_title":           {"en": "The model runs",                                    "id": "Model dijalankan"},
    "how_2_body":            {"en": "A 13-sheet Excel engine computes the profit-maximizing price for each item — guarded by role caps, market context, and confidence-weighted shrinkage.",
                              "id": "Engine Excel 13-sheet menghitung harga yang memaksimalkan keuntungan tiap item — dijaga oleh batas peran, konteks pasar, dan shrinkage berbobot keyakinan."},
    "how_3_title":           {"en": "PDF in your inbox",                                 "id": "PDF di inbox Anda"},
    "how_3_body":            {"en": "Item-by-item recommendations, sensitivity analysis, and a sequencing plan. Forward it to your accountant.",
                              "id": "Rekomendasi per-item, analisis sensitivitas, dan rencana urutan implementasi. Teruskan ke akuntan Anda."},

    "proof_label":           {"en": "Example output · 6-item café menu",                 "id": "Contoh output · menu kafé 6-item"},
    "proof_h2_part1":        {"en": "The kind of clarity you get back — but ",          "id": "Kejelasan seperti ini yang Anda dapat — tetapi "},
    "proof_h2_accent":       {"en": "personalized",                                      "id": "disesuaikan"},
    "proof_h2_part2":        {"en": " to your menu.",                                    "id": " dengan menu Anda."},
    "proof_metric_1":        {"en": "Monthly Δ profit",                                  "id": "Δ Profit bulanan"},
    "proof_metric_2":        {"en": "Lift versus baseline",                              "id": "Kenaikan vs baseline"},
    "proof_metric_3":        {"en": "Items to change",                                   "id": "Item yang diubah"},
    "proof_metric_3_val":    {"en": "5 of 6",                                            "id": "5 dari 6"},
    "proof_note":            {"en": "Real audits are personalized to your specific menu, category mix, and (optionally) competitor context.",
                              "id": "Audit nyata disesuaikan dengan menu, kategori, dan (opsional) konteks kompetitor Anda."},

    "who_label":             {"en": "Who built this",                                    "id": "Tentang pembuat"},
    "who_h2_part1":          {"en": "An independent consultant who ",                   "id": "Konsultan independen yang "},
    "who_h2_accent":         {"en": "obsesses",                                          "id": "fokus penuh"},
    "who_h2_part2":          {"en": " over menu economics.",                             "id": " pada ekonomi menu."},
    "who_body":              {"en": "MarginLab is built and run by <strong>Felix Sean</strong>, an independent consultant focused on pricing for food and beverage operators. The model behind this audit combines Lerner-optimal markup theory, menu-engineering quadrants, and demand-calibrated elasticities — packaged into something a café owner can act on the same day.",
                              "id": "MarginLab dibuat dan dijalankan oleh <strong>Felix Sean</strong>, konsultan independen yang fokus pada penetapan harga untuk pelaku usaha makanan & minuman. Model di balik audit ini menggabungkan teori markup Lerner-optimal, kuadran menu-engineering, dan elastisitas berbasis permintaan — dikemas agar pemilik kafé bisa langsung bertindak di hari yang sama."},

    "cta_strip_h3":          {"en": "Ready to see your numbers?",                        "id": "Siap melihat angka Anda?"},
    "cta_strip_p":           {"en": "Free, takes five minutes, no account required.",   "id": "Gratis, lima menit, tanpa akun."},

    "footer_data_note":      {"en": "We only use your email to send your audit report and follow-ups. We never share it.",
                              "id": "Email Anda hanya digunakan untuk mengirim laporan dan tindak-lanjut. Tidak pernah kami bagikan."},
    "footer_consultant":     {"en": "Consultant access →",                               "id": "Akses konsultan →"},

    # ── Form / Owner Audit ──────────────────────────────────────────────────
    "back_home":             {"en": "← Back to home",                                    "id": "← Kembali ke beranda"},
    "owner_header_eyebrow":  {"en": "Pricing Audit · Free",                              "id": "Audit Harga · Gratis"},
    "owner_header_h1_part1": {"en": "Tell us about ",                                    "id": "Ceritakan tentang "},
    "owner_header_h1_accent":{"en": "your menu",                                         "id": "menu Anda"},
    "owner_header_h1_part2": {"en": ".",                                                  "id": "."},
    "owner_header_p":        {"en": "Enter your items below. We'll run the model and email your PDF report in about thirty seconds.",
                              "id": "Masukkan item Anda di bawah. Kami akan menjalankan model dan mengirim laporan PDF dalam sekitar tiga puluh detik."},

    "sec1_title":            {"en": "About your café",                                   "id": "Tentang kafé Anda"},
    "sec1_desc":             {"en": "Your café name is optional and only used to personalize the PDF report.",
                              "id": "Nama kafé bersifat opsional dan hanya digunakan untuk menyesuaikan laporan PDF."},
    "label_cafe_name":       {"en": "Café name",                                         "id": "Nama kafé"},
    "ph_cafe_name":          {"en": "e.g. The Daily Grind",                              "id": "mis. Kopi Pagi"},
    "label_currency":        {"en": "Currency",                                          "id": "Mata uang"},

    "sec2_title":            {"en": "Your menu",                                         "id": "Menu Anda"},
    "sec2_desc":             {"en": "Add at least one item. We need name, cost, current price, and rough monthly units sold. You can add up to thirty items.",
                              "id": "Tambahkan minimal satu item. Kami butuh nama, biaya, harga saat ini, dan perkiraan jumlah terjual per bulan. Maksimal tiga puluh item."},
    "col_item_name":         {"en": "Item name",                                         "id": "Nama item"},
    "col_category":          {"en": "Category",                                          "id": "Kategori"},
    "col_role":              {"en": "Role",                                              "id": "Peran"},
    "col_cost":              {"en": "Cost",                                              "id": "Biaya"},
    "col_price":             {"en": "Price",                                             "id": "Harga"},
    "col_units":             {"en": "Units / month",                                     "id": "Unit / bulan"},
    "btn_add_item":          {"en": "Add another item",                                  "id": "Tambah item"},
    "btn_remove_last":       {"en": "Remove last",                                       "id": "Hapus terakhir"},
    "expander_comp":         {"en": "Add competitor prices (optional)",                  "id": "Tambah harga kompetitor (opsional)"},
    "comp_caption":          {"en": "Enter prices from up to three nearby cafés for items where market context matters. Leave blank to skip.",
                              "id": "Masukkan harga dari hingga tiga kafé terdekat untuk item yang perlu konteks pasar. Kosongkan jika tidak perlu."},
    "comp_col_item":         {"en": "Item",                                              "id": "Item"},
    "comp_col_1":            {"en": "Competitor 1",                                      "id": "Kompetitor 1"},
    "comp_col_2":            {"en": "Competitor 2",                                      "id": "Kompetitor 2"},
    "comp_col_3":            {"en": "Competitor 3",                                      "id": "Kompetitor 3"},

    "sec3_title":            {"en": "Send the audit",                                    "id": "Kirim audit"},
    "sec3_desc":             {"en": "Your full PDF report — with item-by-item recommendations, sensitivity analysis, and a sequencing plan — will be in your inbox within a minute.",
                              "id": "Laporan PDF lengkap Anda — berisi rekomendasi per-item, analisis sensitivitas, dan rencana urutan — akan masuk ke email Anda dalam satu menit."},
    "label_email":           {"en": "Email address",                                     "id": "Alamat email"},
    "ph_email":              {"en": "you@yourcafe.com",                                  "id": "anda@kafeanda.com"},
    "checkbox_updates":      {"en": "Notify me when MarginLab updates",                  "id": "Beri tahu saya saat MarginLab diperbarui"},
    "btn_submit":            {"en": "Email me my audit  →",                              "id": "Kirim audit ke email saya  →"},
    "spinner_running":       {"en": "Running the model and sending your report…",       "id": "Menjalankan model dan mengirim laporan…"},

    # ── Validation messages ─────────────────────────────────────────────────
    "err_invalid_email":     {"en": "Please enter a valid email address.",               "id": "Masukkan alamat email yang valid."},
    "err_no_items":          {"en": "Please enter at least one menu item before submitting.",
                              "id": "Masukkan minimal satu item menu sebelum mengirim."},
    "err_rate_limit":        {"en": "You've reached the audit limit for this hour. Please try again later, or email felixrichard1208@gmail.com if you need more.",
                              "id": "Anda telah mencapai batas audit untuk satu jam ini. Coba lagi nanti, atau email felixrichard1208@gmail.com jika butuh lebih."},

    # ── Owner success ───────────────────────────────────────────────────────
    "success_h2":            {"en": "Your audit is on its way.",                         "id": "Audit Anda sedang dikirim."},
    "success_lede_part1":    {"en": "We just emailed your full PDF report to ",          "id": "Kami baru saja mengirim laporan PDF lengkap ke "},
    "success_lede_part2":    {"en": "Check your inbox in the next minute or two.",      "id": "Cek inbox Anda dalam satu-dua menit."},
    "success_metric_label":  {"en": "Estimated lift for",                                "id": "Estimasi kenaikan untuk"},
    "success_metric_sub":    {"en": "vs current pricing · monthly",                      "id": "vs harga saat ini · bulanan"},
    "success_default_cafe":  {"en": "your café",                                         "id": "kafé Anda"},
    "success_next_note":     {"en": "The full per-item breakdown, sensitivity analysis, and sequencing plan are in the PDF.<br>Don't see it? Check your spam folder, or email",
                              "id": "Rincian per-item, analisis sensitivitas, dan rencana urutan ada di PDF.<br>Belum diterima? Cek folder spam, atau kirim email ke"},
    "btn_run_another":       {"en": "Run another audit",                                 "id": "Jalankan audit lain"},

    # ── PDF report ──────────────────────────────────────────────────────────
    "pdf_subtitle":          {"en": "Pricing audit · Prepared",                          "id": "Audit harga · Disiapkan"},
    "pdf_brand_caption":     {"en": "PRICING LAB",                                       "id": "LAB PENETAPAN HARGA"},
    "pdf_default_cafe":      {"en": "Your Café",                                         "id": "Kafé Anda"},
    "pdf_metric_lift":       {"en": "Monthly Δ profit",                                  "id": "Δ Profit bulanan"},
    "pdf_metric_lift_sub":   {"en": "versus baseline",                                   "id": "vs baseline"},
    "pdf_metric_conf":       {"en": "Confidence",                                        "id": "Keyakinan"},
    "pdf_metric_conf_sub":   {"en": "weighted across items",                             "id": "berbobot lintas item"},
    "pdf_metric_best":       {"en": "Best opportunity",                                  "id": "Peluang terbaik"},
    "pdf_metric_best_sub":   {"en": "highest Δ profit",                                  "id": "Δ profit tertinggi"},
    "pdf_section_recs":      {"en": "Per-item recommendations",                          "id": "Rekomendasi per-item"},
    "pdf_section_sens":      {"en": "Sensitivity check",                                 "id": "Cek sensitivitas"},
    "pdf_section_next":      {"en": "Next steps",                                        "id": "Langkah berikutnya"},
    "pdf_col_item":          {"en": "Item",                                              "id": "Item"},
    "pdf_col_action":        {"en": "Action",                                            "id": "Tindakan"},
    "pdf_col_from":          {"en": "From",                                              "id": "Dari"},
    "pdf_col_to":            {"en": "To",                                                "id": "Ke"},
    "pdf_col_dpct":          {"en": "Δ%",                                                "id": "Δ%"},
    "pdf_col_dprofit":       {"en": "Δ Profit/mo",                                       "id": "Δ Profit/bln"},
    "pdf_col_quadrant":      {"en": "Quadrant",                                          "id": "Kuadran"},
    "pdf_col_market":        {"en": "Market",                                            "id": "Pasar"},
    "pdf_col_narrative":     {"en": "Narrative",                                         "id": "Catatan"},
    "pdf_sens_cons":         {"en": "Conservative",                                      "id": "Konservatif"},
    "pdf_sens_base":         {"en": "Baseline",                                          "id": "Baseline"},
    "pdf_sens_opt":          {"en": "Optimistic",                                        "id": "Optimistis"},
    "pdf_sens_robust":       {"en": "Recommendation robust?",                            "id": "Apakah rekomendasi robust?"},
    "pdf_next_1_title":      {"en": "Sequence, don't simultaneously change.",            "id": "Lakukan bertahap, jangan sekaligus."},
    "pdf_next_1_body":       {"en": "Start with the single highest-confidence raise. Hold the new price for two weeks. Measure traffic and revenue against the prior two weeks.",
                              "id": "Mulai dari kenaikan dengan keyakinan tertinggi. Tahan harga baru selama dua minggu. Bandingkan traffic dan revenue dengan dua minggu sebelumnya."},
    "pdf_next_2_title":      {"en": "Watch your Traffic Drivers.",                       "id": "Perhatikan Traffic Driver Anda."},
    "pdf_next_2_body":       {"en": "The model caps these tightly. Don't override the cap without a clear plan — these items anchor customer perception of value across the rest of the menu.",
                              "id": "Model membatasi item ini secara ketat. Jangan menaikkan lebih dari batas tanpa rencana yang jelas — item ini menjadi acuan persepsi nilai pelanggan untuk seluruh menu."},
    "pdf_next_3_title":      {"en": "Re-run after one cycle.",                           "id": "Jalankan ulang setelah satu siklus."},
    "pdf_next_3_body":       {"en": "Once you've implemented and observed, re-do the audit with the new numbers. Confidence tiers improve quickly once we have real before/after data.",
                              "id": "Setelah Anda menerapkan dan mengamati hasilnya, ulangi audit dengan angka baru. Tingkat keyakinan akan meningkat cepat setelah ada data sebelum/sesudah yang nyata."},
    "pdf_next_help_h":       {"en": "Want help implementing this?",                      "id": "Butuh bantuan menerapkan ini?"},
    "pdf_next_help_body":    {"en": "Reply to the email this report came in, or book a free 15-minute walkthrough:",
                              "id": "Balas email yang berisi laporan ini, atau jadwalkan walkthrough gratis 15 menit:"},
    "pdf_prepared_by":       {"en": "Prepared by",                                       "id": "Disiapkan oleh"},

    # ── Email templates ─────────────────────────────────────────────────────
    "email_owner_subject":   {"en": "Your MarginLab pricing audit",                      "id": "Audit harga MarginLab Anda"},
    "email_owner_h1":        {"en": "Your MarginLab Pricing Audit",                      "id": "Audit Harga MarginLab Anda"},
    "email_owner_for":       {"en": "for",                                               "id": "untuk"},
    "email_owner_hi":        {"en": "Hi,",                                               "id": "Halo,"},
    "email_owner_p1":        {"en": "Thanks for running a MarginLab pricing audit. Your full report is attached as a PDF — open it on your phone, your laptop, or forward it to your accountant.",
                              "id": "Terima kasih telah menjalankan audit harga MarginLab. Laporan lengkap terlampir sebagai PDF — buka di ponsel, laptop, atau teruskan ke akuntan Anda."},
    "email_owner_metric":    {"en": "Potential monthly profit gain",                     "id": "Potensi kenaikan profit bulanan"},
    "email_owner_metric_sub":{"en": "versus your current pricing",                       "id": "vs harga Anda saat ini"},
    "email_owner_p2":        {"en": "These recommendations come from a profit-maximizing pricing model that accounts for each item's role on your menu, its category, and demand sensitivity. The PDF shows the full breakdown — item by item, with Star / Plowhorse / Puzzle / Dog classification and a plain-language narrative for each move.",
                              "id": "Rekomendasi ini berasal dari model penetapan harga yang memaksimalkan profit dengan mempertimbangkan peran tiap item di menu, kategorinya, dan sensitivitas permintaan. PDF menunjukkan rincian lengkap — per item, dengan klasifikasi Star / Plowhorse / Puzzle / Dog dan catatan dalam bahasa biasa untuk setiap perubahan."},
    "email_owner_p3":        {"en": "<strong>Want help implementing this?</strong> Reply to this email or grab a free 15-min walkthrough:",
                              "id": "<strong>Butuh bantuan menerapkan ini?</strong> Balas email ini atau ambil walkthrough gratis 15 menit:"},
    "email_owner_signoff":   {"en": "— Felix · MarginLab",                               "id": "— Felix · MarginLab"},
    "email_owner_footer":    {"en": "You received this because you ran a free pricing audit at MarginLab.<br>Powered by Lerner-optimal pricing economics.",
                              "id": "Anda menerima ini karena menjalankan audit harga gratis di MarginLab.<br>Didukung oleh ekonomi penetapan harga Lerner-optimal."},

    # ── Follow-ups ──────────────────────────────────────────────────────────
    "email_f1_subject":      {"en": "Following up on your MarginLab audit, {name}",     "id": "Tindak lanjut audit MarginLab Anda, {name}"},
    "email_f1_greeting":     {"en": "Hi {name},",                                        "id": "Halo {name},"},
    "email_f1_p1":           {"en": "Hope your MarginLab audit was useful. Quick note from experience:",
                              "id": "Semoga audit MarginLab Anda bermanfaat. Catatan singkat dari pengalaman:"},
    "email_f1_p2":           {"en": "The numbers in your PDF assume you change prices in <em>one</em> cycle. Most cafés get better results <strong>sequencing</strong> the changes — start with the single highest-confidence raise, hold for two weeks, measure traffic and revenue, then move to the next.",
                              "id": "Angka di PDF Anda mengasumsikan Anda mengubah harga dalam <em>satu</em> siklus. Kebanyakan kafé mendapat hasil lebih baik dengan <strong>menerapkan bertahap</strong> — mulai dari kenaikan dengan keyakinan tertinggi, tahan selama dua minggu, ukur traffic dan revenue, lalu lanjut ke berikutnya."},
    "email_f1_p3":           {"en": "Happy to walk you through a sequencing plan tailored to your menu on a 15-min call:",
                              "id": "Dengan senang hati saya menjelaskan rencana bertahap yang sesuai dengan menu Anda dalam panggilan 15 menit:"},

    "email_f2_subject":      {"en": "One more thing about your pricing",                 "id": "Satu hal lagi tentang harga Anda"},
    "email_f2_p1":           {"en": "One more thing about your pricing:",                "id": "Satu hal lagi tentang harga Anda:"},
    "email_f2_p2":           {"en": "Most café owners I talk to <strong>underprice their signature items by 15–20%</strong> and <strong>overprice their traffic drivers by 5–10%</strong>. If your audit flagged something that surprised you, that's usually why.",
                              "id": "Kebanyakan pemilik kafé yang saya temui <strong>memasang harga signature item 15–20% terlalu rendah</strong> dan <strong>traffic driver 5–10% terlalu tinggi</strong>. Jika audit Anda menandai sesuatu yang mengejutkan, biasanya itulah penyebabnya."},
    "email_f2_p3":           {"en": "Reply if you want to talk it through — happy to look at your specific numbers and tell you what I'd do.",
                              "id": "Balas jika ingin membahasnya — saya dengan senang hati melihat angka Anda dan memberi tahu apa yang akan saya lakukan."},

    # ── Language toggle label ───────────────────────────────────────────────
    "lang_label":            {"en": "Language",                                          "id": "Bahasa"},
    "lang_en":               {"en": "English",                                           "id": "English"},
    "lang_id":               {"en": "Bahasa Indonesia",                                  "id": "Bahasa Indonesia"},
}


SUPPORTED_LANGS = ("en", "id")


def t(key: str, lang: str = "en") -> str:
    """Look up a translation. Falls back to English if missing."""
    entry = STRINGS.get(key)
    if not entry:
        return key  # show the raw key if we forgot to translate — visible bug, easy to find
    return entry.get(lang) or entry.get("en") or key
