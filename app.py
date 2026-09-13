import streamlit as st
import requests
import json
import os
import urllib.parse

st.set_page_config(page_title="Family Stream Finder", page_icon="🍿", layout="centered")

TMDB_API_KEY = st.secrets.get("TMDB_API_KEY", os.getenv("TMDB_API_KEY", ""))
FAMILY_PIN = str(st.secrets.get("FAMILY_PIN", os.getenv("FAMILY_PIN", "1234")))

pin_input = st.text_input("Enter Family PIN", type="password")
if pin_input != FAMILY_PIN:
    st.info("Enter your 4-digit family PIN (default: 1234) to search.")
    st.stop()

def get_direct_link(provider_name, title):
    name = provider_name.lower()
    enc_title = urllib.parse.quote(title)
    
    if "paramount" in name:
        return f"https://www.paramountplus.com/search/?q={enc_title}"
    if "netflix" in name:
        return f"https://www.netflix.com/search?q={enc_title}"
    if "prime" in name or "amazon" in name:
        return f"https://www.amazon.com/s?i=instant-video&k={enc_title}"
    if "max" in name or "hbo" in name:
        return f"https://play.max.com/search?q={enc_title}"
    if "disney" in name:
        return f"https://www.disneyplus.com/search?q={enc_title}"
    if "peacock" in name:
        return f"https://www.peacocktv.com/search?q={enc_title}"
    if "apple" in name:
        return f"https://tv.apple.com/search?term={enc_title}"
    if "hulu" in name:
        return f"https://www.hulu.com/search?q={enc_title}"
    if "tubi" in name:
        return f"https://tubitv.com/search/{enc_title}"
    if "pluto" in name:
        return "https://pluto.tv/search"
    return f"https://www.google.com/search?q=watch+{enc_title}+on+{urllib.parse.quote(provider_name)}"

try:
    with open("profile.json", "r") as f:
        profile = json.load(f)
except FileNotFoundError:
    profile = {"my_subscriptions": [], "owned_movies": []}

my_subs = profile.get("my_subscriptions", [])
owned_movies = [m.strip().lower() for m in profile.get("owned_movies", [])]

st.title("🎬 Where to Watch")
movie_query = st.text_input("Search a movie:", placeholder="e.g. Heat, Gladiator, Inception")

if movie_query:
    query_clean = movie_query.strip().lower()
    
    # 1. Check Fandango Owned Library
    is_owned = any(query_clean == m or query_clean in m for m in owned_movies)
    if is_owned:
        st.success("🎉 **You own this movie on Fandango at Home!**")
        st.link_button("Open Fandango at Home", "https://athome.fandango.com/content/browse/mymovies", use_container_width=True)

    # 2. TMDB Query
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={urllib.parse.quote(movie_query)}&include_adult=false"
    res = requests.get(search_url).json()
    results = res.get("results", [])

    if not results:
        st.warning("No title details found on TMDB.")
    else:
        top_movie = results[0]
        movie_id = top_movie["id"]
        title = top_movie["title"]
        release_year = top_movie.get("release_date", "")[:4]
        poster_path = top_movie.get("poster_path")

        col1, col2 = st.columns([1, 2])
        with col1:
            if poster_path:
                st.image(f"https://image.tmdb.org/t/p/w300{poster_path}", use_container_width=True)
        with col2:
            st.subheader(f"{title} ({release_year})")
            st.write(top_movie.get("overview", "")[:240] + "...")

        prov_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"
        prov_data = requests.get(prov_url).json().get("results", {}).get("US", {})

        flatrate = [p["provider_name"] for p in prov_data.get("flatrate", [])]
        free_ads = [p["provider_name"] for p in prov_data.get("free", []) + prov_data.get("ads", [])]
        rent = [p["provider_name"] for p in prov_data.get("rent", [])]

        matched_subs = []
        for sub in my_subs:
            for p in flatrate:
                if sub.lower().replace("+", "") in p.lower().replace("+", "") or p.lower().replace("+", "") in sub.lower().replace("+", ""):
                    if p not in matched_subs:
                        matched_subs.append(p)

        st.write("---")

        # Active Subscription Matches
        if matched_subs:
            st.success("✅ **Stream Free on Your Subscriptions:**")
            sub_cols = st.columns(min(len(matched_subs), 3))
            for idx, sub in enumerate(matched_subs):
                direct_url = get_direct_link(sub, title)
                with sub_cols[idx % 3]:
                    st.link_button(f"Open {sub}", direct_url, use_container_width=True)

        # Free with Ads
        if free_ads:
            st.info("📺 **Stream 100% Free with Ads:**")
            ad_cols = st.columns(min(len(free_ads), 3))
            for idx, prov in enumerate(set(free_ads[:3])):
                direct_url = get_direct_link(prov, title)
                with ad_cols[idx % 3]:
                    st.link_button(f"Open {prov}", direct_url, use_container_width=True)

        # Paywalled / Not on user subs
        if not matched_subs and not free_ads and not is_owned:
            if flatrate:
                st.warning(f"🔒 Available on services you don't have: {', '.join(flatrate)}")
            if rent:
                st.write(f"💳 Rent or buy available on: {', '.join(rent[:4])}")
            elif not flatrate:
                st.write("Not currently available on major US streaming services.")