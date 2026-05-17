import streamlit as st


def render_news_tab(ticker, articles):
    """Clean news feed with sentiment filter."""
    st.markdown("<p style='font-family:Orbitron;font-size:11px;color:#444;letter-spacing:2px;margin-bottom:16px;'>BERITA & SENTIMEN PASAR</p>", unsafe_allow_html=True)

    if not articles:
        st.info("Tidak ada berita untuk aset ini. Coba refresh atau pilih aset lain.")
        return

    filter_opts = ["SEMUA", "BULLISH", "BEARISH", "NETRAL"]
    selected = st.radio("Filter Sentimen:", filter_opts, horizontal=True, label_visibility="collapsed")
    sel_map = {"SEMUA": "ALL", "NETRAL": "NEUTRAL"}
    sel_key = sel_map.get(selected, selected)
    filtered = [a for a in articles if sel_key == "ALL" or a.get('sentiment_label') == sel_key]

    if not filtered:
        st.warning(f"Tidak ada berita {selected} ditemukan.")
        return

    label_map = {"BULLISH": ("#00ffcc", "▲"), "BEARISH": ("#ff4b4b", "▼"), "NEUTRAL": ("#888", "◆")}

    for a in filtered:
        lbl = a.get('sentiment_label', 'NEUTRAL')
        c, sym = label_map.get(lbl, ("#888", "◆"))
        title   = a.get('title', 'No Title')
        source  = a.get('source', 'Unknown')
        pub     = a.get('published', '')
        url     = a.get('url', '#')
        score   = a.get('sentiment_score', 0)

        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-left:3px solid {c};
                        border-radius:10px;padding:14px 16px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:10px;color:{c};font-family:'Orbitron';letter-spacing:1px;">{sym} {lbl}</span>
                    <span style="font-size:9px;color:#444;">{source} · {str(pub)[:16]}</span>
                </div>
                <a href="{url}" target="_blank" style="color:#ccc;text-decoration:none;font-size:13px;line-height:1.5;">
                    {title}
                </a>
                <div style="margin-top:8px;">
                    <div style="background:#111;border-radius:3px;height:3px;overflow:hidden;width:100%;">
                        <div style="width:{min(abs(score)*200,100):.0f}%;height:100%;background:{c};border-radius:3px;"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.caption(f"Menampilkan {len(filtered)} dari {len(articles)} artikel | Sumber: Google News")
