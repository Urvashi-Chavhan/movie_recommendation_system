# import requests
# import streamlit as st

# # =============================
# # CONFIG
# # =============================
# API_BASE = "https://movie-recommendation-system-9-hftu.onrender.com" or "http://127.0.0.1:8000"
# TMDB_IMG = "https://image.tmdb.org/t/p/w500"

# st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")

# # =============================
# # STYLES (minimal modern)
# # =============================
# st.markdown(
#     """
# <style>
# .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
# .small-muted { color:#6b7280; font-size: 0.92rem; }
# .movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
# .card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
# </style>
# """,
#     unsafe_allow_html=True,
# )

# # =============================
# # STATE + ROUTING (single-file pages)
# # =============================
# if "view" not in st.session_state:
#     st.session_state.view = "home"  # home | details
# if "selected_tmdb_id" not in st.session_state:
#     st.session_state.selected_tmdb_id = None

# qp_view = st.query_params.get("view")
# qp_id = st.query_params.get("id")
# if qp_view in ("home", "details"):
#     st.session_state.view = qp_view
# if qp_id:
#     try:
#         st.session_state.selected_tmdb_id = int(qp_id)
#         st.session_state.view = "details"
#     except:
#         pass


# def goto_home():
#     st.session_state.view = "home"
#     st.query_params["view"] = "home"
#     if "id" in st.query_params:
#         del st.query_params["id"]
#     st.rerun()


# def goto_details(tmdb_id: int):
#     st.session_state.view = "details"
#     st.session_state.selected_tmdb_id = int(tmdb_id)
#     st.query_params["view"] = "details"
#     st.query_params["id"] = str(int(tmdb_id))
#     st.rerun()


# # =============================
# # API HELPERS
# # =============================
# @st.cache_data(ttl=30)  # short cache for autocomplete
# def api_get_json(path: str, params: dict | None = None):
#     try:
#         r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
#         if r.status_code >= 400:
#             return None, f"HTTP {r.status_code}: {r.text[:300]}"
#         return r.json(), None
#     except Exception as e:
#         return None, f"Request failed: {e}"


# def poster_grid(cards, cols=6, key_prefix="grid"):
#     if not cards:
#         st.info("No movies to show.")
#         return

#     rows = (len(cards) + cols - 1) // cols
#     idx = 0
#     for r in range(rows):
#         colset = st.columns(cols)
#         for c in range(cols):
#             if idx >= len(cards):
#                 break
#             m = cards[idx]
#             idx += 1

#             tmdb_id = m.get("tmdb_id")
#             title = m.get("title", "Untitled")
#             poster = m.get("poster_url")

#             with colset[c]:
#                 if poster:
#                     st.image(poster, use_container_width=True)  # FIXED
#                 else:
#                     st.write("🖼️ No poster")

#                 if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
#                     if tmdb_id:
#                         goto_details(tmdb_id)

#                 st.markdown(
#                     f"<div class='movie-title'>{title}</div>", unsafe_allow_html=True
#                 )


# def to_cards_from_tfidf_items(tfidf_items):
#     cards = []
#     for x in tfidf_items or []:
#         tmdb = x.get("tmdb") or {}
#         if tmdb.get("tmdb_id"):
#             cards.append(
#                 {
#                     "tmdb_id": tmdb["tmdb_id"],
#                     "title": tmdb.get("title") or x.get("title") or "Untitled",
#                     "poster_url": tmdb.get("poster_url"),
#                 }
#             )
#     return cards


# # =============================
# # IMPORTANT: Robust TMDB search parsing
# # Supports BOTH API shapes:
# # 1) raw TMDB: {"results":[{id,title,poster_path,...}]}
# # 2) list cards: [{tmdb_id,title,poster_url,...}]
# # =============================
# def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
#     """
#     Returns:
#       suggestions: list[(label, tmdb_id)]
#       cards: list[{tmdb_id,title,poster_url}]
#     """
#     keyword_l = keyword.strip().lower()

#     # A) If API returns dict with 'results'
#     if isinstance(data, dict) and "results" in data:
#         raw = data.get("results") or []
#         raw_items = []
#         for m in raw:
#             title = (m.get("title") or "").strip()
#             tmdb_id = m.get("id")
#             poster_path = m.get("poster_path")
#             if not title or not tmdb_id:
#                 continue
#             raw_items.append(
#                 {
#                     "tmdb_id": int(tmdb_id),
#                     "title": title,
#                     "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
#                     "release_date": m.get("release_date", ""),
#                 }
#             )

#     # B) If API returns already as list
#     elif isinstance(data, list):
#         raw_items = []
#         for m in data:
#             # might be {tmdb_id,title,poster_url}
#             tmdb_id = m.get("tmdb_id") or m.get("id")
#             title = (m.get("title") or "").strip()
#             poster_url = m.get("poster_url")
#             if not title or not tmdb_id:
#                 continue
#             raw_items.append(
#                 {
#                     "tmdb_id": int(tmdb_id),
#                     "title": title,
#                     "poster_url": poster_url,
#                     "release_date": m.get("release_date", ""),
#                 }
#             )
#     else:
#         return [], []

#     # Word-match filtering (contains)
#     matched = [x for x in raw_items if keyword_l in x["title"].lower()]

#     # If nothing matched, fallback to raw list (so never blank)
#     final_list = matched if matched else raw_items

#     # Suggestions = top 10 labels
#     suggestions = []
#     for x in final_list[:10]:
#         year = (x.get("release_date") or "")[:4]
#         label = f"{x['title']} ({year})" if year else x["title"]
#         suggestions.append((label, x["tmdb_id"]))

#     # Cards = top N
#     cards = [
#         {"tmdb_id": x["tmdb_id"], "title": x["title"], "poster_url": x["poster_url"]}
#         for x in final_list[:limit]
#     ]
#     return suggestions, cards


# # =============================
# # SIDEBAR (clean)
# # =============================
# with st.sidebar:
#     st.markdown("## 🎬 Menu")
#     if st.button("🏠 Home"):
#         goto_home()

#     st.markdown("---")
#     st.markdown("### 🏠 Home Feed (only home)")
#     home_category = st.selectbox(
#         "Category",
#         ["trending", "popular", "top_rated", "now_playing", "upcoming"],
#         index=0,
#     )
#     grid_cols = st.slider("Grid columns", 4, 8, 6)

# # =============================
# # HEADER
# # =============================
# st.title("🎬 Movie Recommender")
# st.markdown(
#     "<div class='small-muted'>Type keyword → dropdown suggestions + matching results → open → details + recommendations</div>",
#     unsafe_allow_html=True,
# )
# st.divider()

# # ==========================================================
# # VIEW: HOME
# # ==========================================================
# if st.session_state.view == "home":
#     typed = st.text_input(
#         "Search by movie title (keyword)", placeholder="Type: avenger, batman, love..."
#     )

#     st.divider()

#     # SEARCH MODE (Autocomplete + word-match results)
#     if typed.strip():
#         if len(typed.strip()) < 2:
#             st.caption("Type at least 2 characters for suggestions.")
#         else:
#             data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})

#             if err or data is None:
#                 st.error(f"Search failed: {err}")
#             else:
#                 suggestions, cards = parse_tmdb_search_to_cards(
#                     data, typed.strip(), limit=24
#                 )

#                 # Dropdown
#                 if suggestions:
#                     labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
#                     selected = st.selectbox("Suggestions", labels, index=0)

#                     if selected != "-- Select a movie --":
#                         # map label -> id
#                         label_to_id = {s[0]: s[1] for s in suggestions}
#                         goto_details(label_to_id[selected])
#                 else:
#                     st.info("No suggestions found. Try another keyword.")

#                 st.markdown("### Results")
#                 poster_grid(cards, cols=grid_cols, key_prefix="search_results")

#         st.stop()

#     # HOME FEED MODE
#     st.markdown(f"### 🏠 Home — {home_category.replace('_',' ').title()}")

#     home_cards, err = api_get_json(
#         "/home", params={"category": home_category, "limit": 24}
#     )
#     if err or not home_cards:
#         st.error(f"Home feed failed: {err or 'Unknown error'}")
#         st.stop()

#     poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

# # ==========================================================
# # VIEW: DETAILS
# # ==========================================================
# elif st.session_state.view == "details":
#     tmdb_id = st.session_state.selected_tmdb_id
#     if not tmdb_id:
#         st.warning("No movie selected.")
#         if st.button("← Back to Home"):
#             goto_home()
#         st.stop()

#     # Top bar
#     a, b = st.columns([3, 1])
#     with a:
#         st.markdown("### 📄 Movie Details")
#     with b:
#         if st.button("← Back to Home"):
#             goto_home()

#     # Details (your FastAPI safe route)
#     data, err = api_get_json(f"/movie/id/{tmdb_id}")
#     if err or not data:
#         st.error(f"Could not load details: {err or 'Unknown error'}")
#         st.stop()

#     # Layout: Poster LEFT, Details RIGHT
#     left, right = st.columns([1, 2.4], gap="large")

#     with left:
#         st.markdown("<div class='card'>", unsafe_allow_html=True)
#         if data.get("poster_url"):
#             st.image(data["poster_url"], use_container_width=True)  # FIXED
#         else:
#             st.write("🖼️ No poster")
#         st.markdown("</div>", unsafe_allow_html=True)

#     with right:
#         st.markdown("<div class='card'>", unsafe_allow_html=True)
#         st.markdown(f"## {data.get('title','')}")
#         release = data.get("release_date") or "-"
#         genres = ", ".join([g["name"] for g in data.get("genres", [])]) or "-"
#         st.markdown(
#             f"<div class='small-muted'>Release: {release}</div>", unsafe_allow_html=True
#         )
#         st.markdown(
#             f"<div class='small-muted'>Genres: {genres}</div>", unsafe_allow_html=True
#         )
#         st.markdown("---")
#         st.markdown("### Overview")
#         st.write(data.get("overview") or "No overview available.")
#         st.markdown("</div>", unsafe_allow_html=True)

#     if data.get("backdrop_url"):
#         st.markdown("#### Backdrop")
#         st.image(data["backdrop_url"], use_container_width=True)  # FIXED

#     st.divider()
#     st.markdown("### ✅ Recommendations")

#     # Recommendations (TF-IDF + Genre) via your bundle endpoint
#     title = (data.get("title") or "").strip()
#     if title:
#         bundle, err2 = api_get_json(
#             "/movie/search",
#             params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
#         )

#         if not err2 and bundle:
#             st.markdown("#### 🔎 Similar Movies (TF-IDF)")
#             poster_grid(
#                 to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
#                 cols=grid_cols,
#                 key_prefix="details_tfidf",
#             )

#             st.markdown("#### 🎭 More Like This (Genre)")
#             poster_grid(
#                 bundle.get("genre_recommendations", []),
#                 cols=grid_cols,
#                 key_prefix="details_genre",
#             )
#         else:
#             st.info("Showing Genre recommendations (fallback).")
#             genre_only, err3 = api_get_json(
#                 "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
#             )
#             if not err3 and genre_only:
#                 poster_grid(
#                     genre_only, cols=grid_cols, key_prefix="details_genre_fallback"
#                 )
#             else:
#                 st.warning("No recommendations available right now.")
#     else:
#         st.warning("No title available to compute recommendations.")



# import requests
# import streamlit as st
# import json
# import os
# import bcrypt
# from google import genai

# # =============================
# # CONFIG
# # =============================
# API_BASE = "http://127.0.0.1:8000"
# TMDB_IMG = "https://image.tmdb.org/t/p/w500"
# USER_DB  = "data/users.json"

# st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")

# # =============================
# # STYLES
# # =============================
# st.markdown("""
# <style>
# .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
# .small-muted { color:#6b7280; font-size: 0.92rem; }
# .movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
# .card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }

# /* Auth page styles */
# .auth-container {
#     max-width: 420px;
#     margin: 60px auto;
#     padding: 40px;
#     border-radius: 20px;
#     background: rgba(255,255,255,0.05);
#     border: 1px solid rgba(255,255,255,0.1);
#     box-shadow: 0 8px 32px rgba(0,0,0,0.2);
# }
# .auth-title {
#     text-align: center;
#     font-size: 2rem;
#     font-weight: 700;
#     margin-bottom: 0.2rem;
# }
# .auth-subtitle {
#     text-align: center;
#     color: #6b7280;
#     margin-bottom: 1.5rem;
#     font-size: 0.95rem;
# }
# </style>
# """, unsafe_allow_html=True)


# # =============================
# # DATABASE HELPERS
# # =============================
# def init_db():
#     os.makedirs("data", exist_ok=True)
#     if not os.path.exists(USER_DB):
#         with open(USER_DB, "w") as f:
#             json.dump({}, f)

# def load_users():
#     init_db()
#     with open(USER_DB, "r") as f:
#         return json.load(f)

# def save_users(users):
#     with open(USER_DB, "w") as f:
#         json.dump(users, f, indent=4)

# def user_exists(username):
#     return username in load_users()

# def add_user(username, hashed_password, email):
#     users = load_users()
#     users[username] = {"password": hashed_password, "email": email}
#     save_users(users)

# def get_user(username):
#     return load_users().get(username, None)


# # =============================
# # AUTH HELPERS
# # =============================
# def hash_password(password):
#     return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# def verify_password(password, hashed):
#     return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# # =============================
# # CHATBOT HELPER
# # =============================

# client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
# client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# from google import genai

# client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# def get_chatbot_response(conversation_history, user_message):

#     prompt = """
#     You are CineBot 🎬, an expert AI movie assistant.
#     Recommend movies, explain plots, suggest genres, and talk about cinema.
#     Keep answers short and friendly.
#     """

#     for msg in conversation_history:
#         prompt += f"\n{msg['role']}: {msg['content']}"

#     prompt += f"\nuser: {user_message}"

#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt
#     )

#     return response.text
#     prompt = "You are CineBot 🎬, a movie expert.\n\n"

#     for msg in conversation_history:
#         role = msg["role"]
#         content = msg["content"]
#         prompt += f"{role}: {content}\n"

#     prompt += f"user: {user_message}"

#     response = model.generate_content(prompt)
#     return response.text

#     system_prompt = """
#     You are CineBot 🎬, an expert AI movie assistant.
#     You help users with:
#     - Movie recommendations based on their mood, genre, or preferences
#     - Information about any movie (plot, cast, director, year)
#     - Comparing movies and finding similar ones
#     - Suggesting movies by language (Hindi, English, Tamil, etc.)
#     - Bollywood, Hollywood, and world cinema

#     Keep responses friendly, short, and engaging.
#     Use emojis occasionally to keep it fun.
#     If asked something unrelated to movies, politely redirect to movies.
#     """

#     messages = [{"role": "system", "content": system_prompt}]
#     messages += conversation_history
#     messages.append({"role": "user", "content": user_message})

#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=messages,
#         max_tokens=500,
#         temperature=0.7,
#     )
#     return response.choices[0].message.content


# # =============================
# # SESSION STATE INIT
# # =============================
# def init_session():
#     defaults = {
#         "logged_in":    False,
#         "username":     "",
#         "auth_page":    "login",   # login | signup
#         "view":         "home",    # home | details
#         "selected_tmdb_id": None,
#         "chat_history": [],
#     }
#     for k, v in defaults.items():
#         if k not in st.session_state:
#             st.session_state[k] = v

# init_session()


# # =============================
# # ROUTING (query params)
# # =============================
# qp_view = st.query_params.get("view")
# qp_id   = st.query_params.get("id")
# if qp_view in ("home", "details"):
#     st.session_state.view = qp_view
# if qp_id:
#     try:
#         st.session_state.selected_tmdb_id = int(qp_id)
#         st.session_state.view = "details"
#     except:
#         pass

# def goto_home():
#     st.session_state.view = "home"
#     st.query_params["view"] = "home"
#     if "id" in st.query_params:
#         del st.query_params["id"]
#     st.rerun()

# def goto_details(tmdb_id: int):
#     st.session_state.view = "details"
#     st.session_state.selected_tmdb_id = int(tmdb_id)
#     st.query_params["view"] = "details"
#     st.query_params["id"]   = str(int(tmdb_id))
#     st.rerun()


# # =============================
# # API HELPERS
# # =============================
# @st.cache_data(ttl=30)
# def api_get_json(path: str, params: dict | None = None, timeout=60):
#     try:
#         r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
#         if r.status_code >= 400:
#             return None, f"HTTP {r.status_code}: {r.text[:300]}"
#         return r.json(), None
#     except Exception as e:
#         return None, f"Request failed: {e}"

# def poster_grid(cards, cols=6, key_prefix="grid"):
#     if not cards:
#         st.info("No movies to show.")
#         return
#     rows = (len(cards) + cols - 1) // cols
#     idx  = 0
#     for r in range(rows):
#         colset = st.columns(cols)
#         for c in range(cols):
#             if idx >= len(cards):
#                 break
#             m = cards[idx]; idx += 1
#             tmdb_id = m.get("tmdb_id")
#             title   = m.get("title", "Untitled")
#             poster  = m.get("poster_url")
#             with colset[c]:
#                 if poster:
#                     st.image(poster, use_container_width=True)
#                 else:
#                     st.write("🖼️ No poster")
#                 if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
#                     if tmdb_id:
#                         goto_details(tmdb_id)
#                 st.markdown(f"<div class='movie-title'>{title}</div>", unsafe_allow_html=True)

# def to_cards_from_tfidf_items(tfidf_items):
#     cards = []
#     for x in tfidf_items or []:
#         tmdb = x.get("tmdb") or {}
#         if tmdb.get("tmdb_id"):
#             cards.append({
#                 "tmdb_id":    tmdb["tmdb_id"],
#                 "title":      tmdb.get("title") or x.get("title") or "Untitled",
#                 "poster_url": tmdb.get("poster_url"),
#             })
#     return cards

# def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
#     keyword_l = keyword.strip().lower()
#     if isinstance(data, dict) and "results" in data:
#         raw = data.get("results") or []
#         raw_items = []
#         for m in raw:
#             title      = (m.get("title") or "").strip()
#             tmdb_id    = m.get("id")
#             poster_path= m.get("poster_path")
#             if not title or not tmdb_id:
#                 continue
#             raw_items.append({
#                 "tmdb_id":      int(tmdb_id),
#                 "title":        title,
#                 "poster_url":   f"{TMDB_IMG}{poster_path}" if poster_path else None,
#                 "release_date": m.get("release_date", ""),
#             })
#     elif isinstance(data, list):
#         raw_items = []
#         for m in data:
#             tmdb_id   = m.get("tmdb_id") or m.get("id")
#             title     = (m.get("title") or "").strip()
#             poster_url= m.get("poster_url")
#             if not title or not tmdb_id:
#                 continue
#             raw_items.append({
#                 "tmdb_id":      int(tmdb_id),
#                 "title":        title,
#                 "poster_url":   poster_url,
#                 "release_date": m.get("release_date", ""),
#             })
#     else:
#         return [], []

#     matched    = [x for x in raw_items if keyword_l in x["title"].lower()]
#     final_list = matched if matched else raw_items

#     suggestions = []
#     for x in final_list[:10]:
#         year  = (x.get("release_date") or "")[:4]
#         label = f"{x['title']} ({year})" if year else x["title"]
#         suggestions.append((label, x["tmdb_id"]))

#     cards = [{"tmdb_id": x["tmdb_id"], "title": x["title"], "poster_url": x["poster_url"]}
#              for x in final_list[:limit]]
#     return suggestions, cards


# # =============================
# # LOGIN PAGE
# # =============================
# def show_login():
#     st.markdown("<div class='auth-title'>🎬 Movie Recommender</div>", unsafe_allow_html=True)
#     st.markdown("<div class='auth-subtitle'>Login to continue</div>",  unsafe_allow_html=True)
#     st.markdown("---")

#     username = st.text_input("👤 Username", key="login_username")
#     password = st.text_input("🔒 Password", type="password", key="login_password")

#     if st.button("Login", use_container_width=True, type="primary"):
#         if not username or not password:
#             st.error("⚠️ Please enter both username and password!")
#         else:
#             user = get_user(username)
#             if user is None:
#                 st.error("❌ Username not found!")
#             elif not verify_password(password, user["password"]):
#                 st.error("❌ Incorrect password!")
#             else:
#                 st.session_state.logged_in = True
#                 st.session_state.username  = username
#                 st.success(f"✅ Welcome back, {username}!")
#                 st.rerun()

#     st.markdown("---")
#     st.markdown("Don't have an account?")
#     if st.button("Create Account →", use_container_width=True):
#         st.session_state.auth_page = "signup"
#         st.rerun()


# # =============================
# # SIGNUP PAGE
# # =============================
# def show_signup():
#     st.markdown("<div class='auth-title'>🎬 Join Movie Recommender</div>", unsafe_allow_html=True)
#     st.markdown("<div class='auth-subtitle'>Create your free account</div>", unsafe_allow_html=True)
#     st.markdown("---")

#     email    = st.text_input("📧 Email",            key="signup_email")
#     username = st.text_input("👤 Username",          key="signup_username")
#     password = st.text_input("🔒 Password",          type="password", key="signup_password")
#     confirm  = st.text_input("🔒 Confirm Password",  type="password", key="signup_confirm")

#     if st.button("Create Account", use_container_width=True, type="primary"):
#         if not email or not username or not password:
#             st.error("⚠️ All fields are required!")
#         elif len(username) < 3:
#             st.error("⚠️ Username must be at least 3 characters!")
#         elif len(password) < 6:
#             st.error("⚠️ Password must be at least 6 characters!")
#         elif password != confirm:
#             st.error("⚠️ Passwords do not match!")
#         elif user_exists(username):
#             st.error("⚠️ Username already taken. Try another!")
#         else:
#             add_user(username, hash_password(password), email)
#             st.success("✅ Account created! Please login now.")
#             st.session_state.auth_page = "login"
#             st.rerun()

#     st.markdown("---")
#     st.markdown("Already have an account?")
#     if st.button("Go to Login →", use_container_width=True):
#         st.session_state.auth_page = "login"
#         st.rerun()


# # =============================
# # MAIN APP (after login)
# # =============================
# def show_main_app():

#     # ── Sidebar ──────────────────────────────────────────
#     with st.sidebar:
#         st.markdown("## 🎬 Menu")

#         # User info
#         st.markdown(f"### 👋 Hello, {st.session_state.username}!")
#         st.markdown("---")

#         if st.button("🏠 Home"):
#             goto_home()

#         st.markdown("---")
#         st.markdown("### 🏠 Home Feed")
#         home_category = st.selectbox(
#             "Category",
#             ["trending", "popular", "top_rated", "now_playing", "upcoming"],
#             index=0,
#         )
#         grid_cols = st.slider("Grid columns", 4, 8, 6)

#         st.markdown("---")
#         if st.button("🚪 Logout", use_container_width=True):
#             st.session_state.logged_in    = False
#             st.session_state.username     = ""
#             st.session_state.auth_page    = "login"
#             st.session_state.chat_history = []
#             st.rerun()

#     # ── Header ───────────────────────────────────────────
#     st.title("🎬 Movie Recommender")
#     st.markdown(
#         "<div class='small-muted'>Type keyword → dropdown suggestions + matching results → open → details + recommendations</div>",
#         unsafe_allow_html=True,
#     )
#     st.divider()

#     # ── Tabs ─────────────────────────────────────────────
#     tab1, tab2 = st.tabs(["🎬 Movies", "🤖 CineBot Chat"])

#     # ── TAB 1: Movie Recommender (your original code) ────
#     with tab1:

#         # VIEW: HOME
#         if st.session_state.view == "home":
#             typed = st.text_input(
#                 "Search by movie title (keyword)",
#                 placeholder="Type: avenger, batman, love...",
#             )
#             st.divider()

#             if typed.strip():
#                 if len(typed.strip()) < 2:
#                     st.caption("Type at least 2 characters for suggestions.")
#                 else:
#                     data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})
#                     if err or data is None:
#                         st.error(f"Search failed: {err}")
#                     else:
#                         suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)
#                         if suggestions:
#                             labels   = ["-- Select a movie --"] + [s[0] for s in suggestions]
#                             selected = st.selectbox("Suggestions", labels, index=0)
#                             if selected != "-- Select a movie --":
#                                 label_to_id = {s[0]: s[1] for s in suggestions}
#                                 goto_details(label_to_id[selected])
#                         else:
#                             st.info("No suggestions found. Try another keyword.")

#                         st.markdown("### Results")
#                         poster_grid(cards, cols=grid_cols, key_prefix="search_results")
#                 st.stop()

#             # HOME FEED
#             st.markdown(f"### 🏠 Home — {home_category.replace('_',' ').title()}")
#             home_cards, err = api_get_json("/home", params={"category": home_category, "limit": 24})
#             if err or not home_cards:
#                 st.error(f"Home feed failed: {err or 'Unknown error'}")
#                 st.stop()
#             poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

#         # VIEW: DETAILS
#         elif st.session_state.view == "details":
#             tmdb_id = st.session_state.selected_tmdb_id
#             if not tmdb_id:
#                 st.warning("No movie selected.")
#                 if st.button("← Back to Home"):
#                     goto_home()
#                 st.stop()

#             a, b = st.columns([3, 1])
#             with a:
#                 st.markdown("### 📄 Movie Details")
#             with b:
#                 if st.button("← Back to Home"):
#                     goto_home()

#             data, err = api_get_json(f"/movie/id/{tmdb_id}")
#             if err or not data:
#                 st.error(f"Could not load details: {err or 'Unknown error'}")
#                 st.stop()

#             left, right = st.columns([1, 2.4], gap="large")
#             with left:
#                 st.markdown("<div class='card'>", unsafe_allow_html=True)
#                 if data.get("poster_url"):
#                     st.image(data["poster_url"], use_container_width=True)
#                 else:
#                     st.write("🖼️ No poster")
#                 st.markdown("</div>", unsafe_allow_html=True)

#             with right:
#                 st.markdown("<div class='card'>", unsafe_allow_html=True)
#                 st.markdown(f"## {data.get('title','')}")
#                 release = data.get("release_date") or "-"
#                 genres  = ", ".join([g["name"] for g in data.get("genres", [])]) or "-"
#                 st.markdown(f"<div class='small-muted'>Release: {release}</div>", unsafe_allow_html=True)
#                 st.markdown(f"<div class='small-muted'>Genres: {genres}</div>",   unsafe_allow_html=True)
#                 st.markdown("---")
#                 st.markdown("### Overview")
#                 st.write(data.get("overview") or "No overview available.")
#                 st.markdown("</div>", unsafe_allow_html=True)

#             if data.get("backdrop_url"):
#                 st.markdown("#### Backdrop")
#                 st.image(data["backdrop_url"], use_container_width=True)

#             st.divider()
#             st.markdown("### ✅ Recommendations")

#             title = (data.get("title") or "").strip()
#             if title:
#                 bundle, err2 = api_get_json(
#                     "/movie/search",
#                     params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
#                 )
#                 if not err2 and bundle:
#                     st.markdown("#### 🔎 Similar Movies (TF-IDF)")
#                     poster_grid(
#                         to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
#                         cols=grid_cols, key_prefix="details_tfidf",
#                     )
#                     st.markdown("#### 🎭 More Like This (Genre)")
#                     poster_grid(
#                         bundle.get("genre_recommendations", []),
#                         cols=grid_cols, key_prefix="details_genre",
#                     )
#                 else:
#                     st.info("Showing Genre recommendations (fallback).")
#                     genre_only, err3 = api_get_json(
#                         "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
#                     )
#                     if not err3 and genre_only:
#                         poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
#                     else:
#                         st.warning("No recommendations available right now.")
#             else:
#                 st.warning("No title available to compute recommendations.")

#     # ── TAB 2: CineBot Chatbot ────────────────────────────
#     with tab2:
#         st.header("🤖 CineBot — Your Movie Assistant")
#         st.caption("Ask me anything about movies — recommendations, plot, cast, and more!")
#         st.divider()

#         # Display chat history
#         for message in st.session_state.chat_history:
#             with st.chat_message(message["role"]):
#                 st.markdown(message["content"])

#         # Chat input
#         user_input = st.chat_input("Ask me about movies... 🎬")

#         if user_input:
#             # Show user message
#             with st.chat_message("user"):
#                 st.markdown(user_input)

#             # Get and show bot response
#             with st.chat_message("assistant"):
#                 with st.spinner("CineBot is thinking..."):
#                     try:
#                         response = get_chatbot_response(
#                             st.session_state.chat_history,
#                             user_input,
#                         )
#                     except Exception as e:
#                         response = f"⚠️ Sorry, I ran into an error: {e}. Please check your API key in secrets."
#                 st.markdown(response)

#             # Save to history
#             st.session_state.chat_history.append({"role": "user",      "content": user_input})
#             st.session_state.chat_history.append({"role": "assistant",  "content": response})

#         # Clear chat button
#         if st.session_state.chat_history:
#             st.divider()
#             if st.button("🗑️ Clear Chat History"):
#                 st.session_state.chat_history = []
#                 st.rerun()


# # =============================
# # APP ROUTER — Entry Point
# # =============================
# if not st.session_state.logged_in:
#     # Center the auth form
#     _, col, _ = st.columns([1, 1.2, 1])
#     with col:
#         if st.session_state.auth_page == "signup":
#             show_signup()
#         else:
#             show_login()
# else:
#     show_main_app()









import requests
import streamlit as st
import json
import os
import bcrypt
from google import genai

# =============================
# CONFIG
# =============================

API_BASE = "https://movie-recommendation-system-9-hftu.onrender.com"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
USER_DB  = "data/users.json"

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")

# =============================
# STYLES
# =============================
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
.small-muted { color:#6b7280; font-size: 0.92rem; }
.movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
.card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
.auth-title {
    text-align: center;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.auth-subtitle {
    text-align: center;
    color: #6b7280;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)


# =============================
# DATABASE HELPERS
# =============================
def init_db():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USER_DB):
        with open(USER_DB, "w") as f:
            json.dump({}, f)

def load_users():
    init_db()
    with open(USER_DB, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)

def user_exists(username):
    return username in load_users()

def add_user(username, hashed_password, email):
    users = load_users()
    users[username] = {"password": hashed_password, "email": email}
    save_users(users)

def get_user(username):
    return load_users().get(username, None)


# =============================
# AUTH HELPERS
# =============================
def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# =============================
# CHATBOT HELPER  ✅ FIXED - clean single version
# =============================
def get_chatbot_response(conversation_history, user_message):
    # ✅ Client created INSIDE function — safe, no startup crash
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # Build full prompt with conversation history
    prompt = """You are CineBot 🎬, an expert AI movie assistant.
You help users with:
- Movie recommendations based on mood, genre, or preferences
- Information about any movie (plot, cast, director, year)
- Comparing movies and finding similar ones
- Suggesting movies by language (Hindi, English, Tamil, etc.)
- Bollywood, Hollywood, and world cinema

Keep responses friendly, short, and engaging.
Use emojis occasionally to keep it fun.
If asked something unrelated to movies, politely redirect to movies.

Conversation so far:
"""
    for msg in conversation_history:
        role = "User" if msg["role"] == "user" else "CineBot"
        prompt += f"{role}: {msg['content']}\n"

    prompt += f"User: {user_message}\nCineBot:"

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text


# =============================
# SESSION STATE INIT
# =============================
def init_session():
    defaults = {
        "logged_in":        False,
        "username":         "",
        "auth_page":        "login",
        "view":             "home",
        "selected_tmdb_id": None,
        "chat_history":     [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# =============================
# ROUTING (query params)
# =============================
qp_view = st.query_params.get("view")
qp_id   = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except:
        pass

def goto_home():
    st.session_state.view = "home"
    st.query_params["view"] = "home"
    if "id" in st.query_params:
        del st.query_params["id"]
    st.rerun()

def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"]   = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"

def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return
    rows = (len(cards) + cols - 1) // cols
    idx  = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]; idx += 1
            tmdb_id = m.get("tmdb_id")
            title   = m.get("title", "Untitled")
            poster  = m.get("poster_url")
            with colset[c]:
                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.write("🖼️ No poster")
                if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(tmdb_id)
                st.markdown(f"<div class='movie-title'>{title}</div>", unsafe_allow_html=True)

def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append({
                "tmdb_id":    tmdb["tmdb_id"],
                "title":      tmdb.get("title") or x.get("title") or "Untitled",
                "poster_url": tmdb.get("poster_url"),
            })
    return cards

def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()
    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title       = (m.get("title") or "").strip()
            tmdb_id     = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id":      int(tmdb_id),
                "title":        title,
                "poster_url":   f"{TMDB_IMG}{poster_path}" if poster_path else None,
                "release_date": m.get("release_date", ""),
            })
    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id    = m.get("tmdb_id") or m.get("id")
            title      = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or not tmdb_id:
                continue
            raw_items.append({
                "tmdb_id":      int(tmdb_id),
                "title":        title,
                "poster_url":   poster_url,
                "release_date": m.get("release_date", ""),
            })
    else:
        return [], []

    matched    = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    suggestions = []
    for x in final_list[:10]:
        year  = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    cards = [{"tmdb_id": x["tmdb_id"], "title": x["title"], "poster_url": x["poster_url"]}
             for x in final_list[:limit]]
    return suggestions, cards


# =============================
# LOGIN PAGE
# =============================
def show_login():
    st.markdown("<div class='auth-title'>🎬 Movie Recommender</div>", unsafe_allow_html=True)
    st.markdown("<div class='auth-subtitle'>Login to continue</div>", unsafe_allow_html=True)
    st.markdown("---")

    username = st.text_input("👤 Username", key="login_username")
    password = st.text_input("🔒 Password", type="password", key="login_password")

    if st.button("Login", use_container_width=True, type="primary"):
        if not username or not password:
            st.error("⚠️ Please enter both username and password!")
        else:
            user = get_user(username)
            if user is None:
                st.error("❌ Username not found!")
            elif not verify_password(password, user["password"]):
                st.error("❌ Incorrect password!")
            else:
                st.session_state.logged_in = True
                st.session_state.username  = username
                st.success(f"✅ Welcome back, {username}!")
                st.rerun()

    st.markdown("---")
    st.markdown("Don't have an account?")
    if st.button("Create Account →", use_container_width=True):
        st.session_state.auth_page = "signup"
        st.rerun()


# =============================
# SIGNUP PAGE
# =============================
def show_signup():
    st.markdown("<div class='auth-title'>🎬 Join Movie Recommender</div>", unsafe_allow_html=True)
    st.markdown("<div class='auth-subtitle'>Create your free account</div>", unsafe_allow_html=True)
    st.markdown("---")

    email    = st.text_input("📧 Email",           key="signup_email")
    username = st.text_input("👤 Username",         key="signup_username")
    password = st.text_input("🔒 Password",         type="password", key="signup_password")
    confirm  = st.text_input("🔒 Confirm Password", type="password", key="signup_confirm")

    if st.button("Create Account", use_container_width=True, type="primary"):
        if not email or not username or not password:
            st.error("⚠️ All fields are required!")
        elif len(username) < 3:
            st.error("⚠️ Username must be at least 3 characters!")
        elif len(password) < 6:
            st.error("⚠️ Password must be at least 6 characters!")
        elif password != confirm:
            st.error("⚠️ Passwords do not match!")
        elif user_exists(username):
            st.error("⚠️ Username already taken. Try another!")
        else:
            add_user(username, hash_password(password), email)
            st.success("✅ Account created! Please login now.")
            st.session_state.auth_page = "login"
            st.rerun()

    st.markdown("---")
    st.markdown("Already have an account?")
    if st.button("Go to Login →", use_container_width=True):
        st.session_state.auth_page = "login"
        st.rerun()


# =============================
# MAIN APP
# =============================
def show_main_app():

    # ── Sidebar ──────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🎬 Menu")
        st.markdown(f"### 👋 Hello, {st.session_state.username}!")
        st.markdown("---")

        if st.button("🏠 Home"):
            goto_home()

        st.markdown("---")
        st.markdown("### 🏠 Home Feed")
        home_category = st.selectbox(
            "Category",
            ["trending", "popular", "top_rated", "now_playing", "upcoming"],
            index=0,
        )
        grid_cols = st.slider("Grid columns", 4, 8, 6)

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in    = False
            st.session_state.username     = ""
            st.session_state.auth_page    = "login"
            st.session_state.chat_history = []
            st.rerun()

    # ── Header ───────────────────────────────────────────
    st.title("🎬 Movie Recommender")
    st.markdown(
        "<div class='small-muted'>Search movies → open details → get recommendations</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Tabs ─────────────────────────────────────────────
    tab1, tab2 = st.tabs(["🎬 Movies", "🤖 CineBot Chat"])

    # ── TAB 1: Movies ────────────────────────────────────
    with tab1:

        if st.session_state.view == "home":
            typed = st.text_input(
                "Search by movie title (keyword)",
                placeholder="Type: avenger, batman, love...",
            )
            st.divider()

            if typed.strip():
                if len(typed.strip()) < 2:
                    st.caption("Type at least 2 characters for suggestions.")
                else:
                    data, err = api_get_json("/tmdb/search", params={"query": typed.strip()})
                    if err or data is None:
                        st.error(f"Search failed: {err}")
                    else:
                        suggestions, cards = parse_tmdb_search_to_cards(data, typed.strip(), limit=24)
                        if suggestions:
                            labels   = ["-- Select a movie --"] + [s[0] for s in suggestions]
                            selected = st.selectbox("Suggestions", labels, index=0)
                            if selected != "-- Select a movie --":
                                label_to_id = {s[0]: s[1] for s in suggestions}
                                goto_details(label_to_id[selected])
                        else:
                            st.info("No suggestions found. Try another keyword.")
                        st.markdown("### Results")
                        poster_grid(cards, cols=grid_cols, key_prefix="search_results")
                st.stop()

            st.markdown(f"### 🏠 Home — {home_category.replace('_',' ').title()}")
            home_cards, err = api_get_json("/home", params={"category": home_category, "limit": 24})
            if err or not home_cards:
                st.error(f"Home feed failed: {err or 'Unknown error'}")
                st.stop()
            poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

        elif st.session_state.view == "details":
            tmdb_id = st.session_state.selected_tmdb_id
            if not tmdb_id:
                st.warning("No movie selected.")
                if st.button("← Back to Home"):
                    goto_home()
                st.stop()

            a, b = st.columns([3, 1])
            with a:
                st.markdown("### 📄 Movie Details")
            with b:
                if st.button("← Back to Home"):
                    goto_home()

            data, err = api_get_json(f"/movie/id/{tmdb_id}")
            if err or not data:
                st.error(f"Could not load details: {err or 'Unknown error'}")
                st.stop()

            left, right = st.columns([1, 2.4], gap="large")
            with left:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                if data.get("poster_url"):
                    st.image(data["poster_url"], use_container_width=True)
                else:
                    st.write("🖼️ No poster")
                st.markdown("</div>", unsafe_allow_html=True)

            with right:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"## {data.get('title','')}")
                release = data.get("release_date") or "-"
                genres  = ", ".join([g["name"] for g in data.get("genres", [])]) or "-"
                st.markdown(f"<div class='small-muted'>Release: {release}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='small-muted'>Genres: {genres}</div>",   unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("### Overview")
                st.write(data.get("overview") or "No overview available.")
                st.markdown("</div>", unsafe_allow_html=True)

            if data.get("backdrop_url"):
                st.markdown("#### Backdrop")
                st.image(data["backdrop_url"], use_container_width=True)

            st.divider()
            st.markdown("### ✅ Recommendations")

            title = (data.get("title") or "").strip()
            if title:
                bundle, err2 = api_get_json(
                    "/movie/search",
                    params={"query": title, "tfidf_top_n": 12, "genre_limit": 12},
                )
                if not err2 and bundle:
                    st.markdown("#### 🔎 Similar Movies (TF-IDF)")
                    poster_grid(
                        to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
                        cols=grid_cols, key_prefix="details_tfidf",
                    )
                    st.markdown("#### 🎭 More Like This (Genre)")
                    poster_grid(
                        bundle.get("genre_recommendations", []),
                        cols=grid_cols, key_prefix="details_genre",
                    )
                else:
                    st.info("Showing Genre recommendations (fallback).")
                    genre_only, err3 = api_get_json(
                        "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
                    )
                    if not err3 and genre_only:
                        poster_grid(genre_only, cols=grid_cols, key_prefix="details_genre_fallback")
                    else:
                        st.warning("No recommendations available right now.")
            else:
                st.warning("No title available to compute recommendations.")

    # ── TAB 2: CineBot ───────────────────────────────────
    with tab2:
        st.header("🤖 CineBot — Your Movie Assistant")
        st.caption("Ask me anything about movies — recommendations, plot, cast, and more!")
        st.divider()

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Ask me about movies... 🎬")

        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("CineBot is thinking..."):
                    try:
                        response = get_chatbot_response(
                            st.session_state.chat_history,
                            user_input,
                        )
                    except Exception as e:
                        response = f"⚠️ Error: {e}. Please check your GEMINI_API_KEY in Streamlit secrets."
                st.markdown(response)

            st.session_state.chat_history.append({"role": "user",      "content": user_input})
            st.session_state.chat_history.append({"role": "assistant",  "content": response})

        if st.session_state.chat_history:
            st.divider()
            if st.button("🗑️ Clear Chat History"):
                st.session_state.chat_history = []
                st.rerun()


# =============================
# APP ROUTER
# =============================
if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        if st.session_state.auth_page == "signup":
            show_signup()
        else:
            show_login()
else:
    show_main_app()


