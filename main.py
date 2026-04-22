# import os
# import pickle
# from typing import Optional, List, Dict, Any, Tuple

# import numpy as np
# import pandas as pd
# import httpx
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from dotenv import load_dotenv


# # =========================
# # ENV
# # =========================
# load_dotenv()
# TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# TMDB_BASE = "https://api.themoviedb.org/3"
# TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"

# if not TMDB_API_KEY:
#     # Don't crash import-time in production if you prefer; but for you better fail early:
#     raise RuntimeError("TMDB_API_KEY missing. Put it in .env as TMDB_API_KEY=xxxx")


# # =========================
# # FASTAPI APP
# # =========================
# app = FastAPI(title="Movie Recommender API", version="3.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # for local streamlit
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # =========================
# # PICKLE GLOBALS
# # =========================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DF_PATH = os.path.join(BASE_DIR, "df.pkl")
# INDICES_PATH = os.path.join(BASE_DIR, "indices.pkl")
# TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
# TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")

# df: Optional[pd.DataFrame] = None
# indices_obj: Any = None
# tfidf_matrix: Any = None
# tfidf_obj: Any = None

# TITLE_TO_IDX: Optional[Dict[str, int]] = None


# # =========================
# # MODELS
# # =========================
# class TMDBMovieCard(BaseModel):
#     tmdb_id: int
#     title: str
#     poster_url: Optional[str] = None
#     release_date: Optional[str] = None
#     vote_average: Optional[float] = None


# class TMDBMovieDetails(BaseModel):
#     tmdb_id: int
#     title: str
#     overview: Optional[str] = None
#     release_date: Optional[str] = None
#     poster_url: Optional[str] = None
#     backdrop_url: Optional[str] = None
#     genres: List[dict] = []


# class TFIDFRecItem(BaseModel):
#     title: str
#     score: float
#     tmdb: Optional[TMDBMovieCard] = None


# class SearchBundleResponse(BaseModel):
#     query: str
#     movie_details: TMDBMovieDetails
#     tfidf_recommendations: List[TFIDFRecItem]
#     genre_recommendations: List[TMDBMovieCard]


# # =========================
# # UTILS
# # =========================
# def _norm_title(t: str) -> str:
#     return str(t).strip().lower()


# def make_img_url(path: Optional[str]) -> Optional[str]:
#     if not path:
#         return None
#     return f"{TMDB_IMG_500}{path}"


# async def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Safe TMDB GET:
#     - Network errors -> 502
#     - TMDB API errors -> 502 with detail
#     """
#     q = dict(params)
#     q["api_key"] = TMDB_API_KEY

#     try:
#         async with httpx.AsyncClient(timeout=20) as client:
#             r = await client.get(f"{TMDB_BASE}{path}", params=q)
#     except httpx.RequestError as e:
#         raise HTTPException(
#             status_code=502,
#             detail=f"TMDB request error: {type(e).__name__} | {repr(e)}",
#         )

#     if r.status_code != 200:
#         raise HTTPException(
#             status_code=502, detail=f"TMDB error {r.status_code}: {r.text}"
#         )

#     return r.json()


# async def tmdb_cards_from_results(
#     results: List[dict], limit: int = 20
# ) -> List[TMDBMovieCard]:
#     out: List[TMDBMovieCard] = []
#     for m in (results or [])[:limit]:
#         out.append(
#             TMDBMovieCard(
#                 tmdb_id=int(m["id"]),
#                 title=m.get("title") or m.get("name") or "",
#                 poster_url=make_img_url(m.get("poster_path")),
#                 release_date=m.get("release_date"),
#                 vote_average=m.get("vote_average"),
#             )
#         )
#     return out


# async def tmdb_movie_details(movie_id: int) -> TMDBMovieDetails:
#     data = await tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})
#     return TMDBMovieDetails(
#         tmdb_id=int(data["id"]),
#         title=data.get("title") or "",
#         overview=data.get("overview"),
#         release_date=data.get("release_date"),
#         poster_url=make_img_url(data.get("poster_path")),
#         backdrop_url=make_img_url(data.get("backdrop_path")),
#         genres=data.get("genres", []) or [],
#     )


# async def tmdb_search_movies(query: str, page: int = 1) -> Dict[str, Any]:
#     """
#     Raw TMDB response for keyword search (MULTIPLE results).
#     Streamlit will use this for suggestions and grid.
#     """
#     return await tmdb_get(
#         "/search/movie",
#         {
#             "query": query,
#             "include_adult": "false",
#             "language": "en-US",
#             "page": page,
#         },
#     )


# async def tmdb_search_first(query: str) -> Optional[dict]:
#     data = await tmdb_search_movies(query=query, page=1)
#     results = data.get("results", [])
#     return results[0] if results else None


# # =========================
# # TF-IDF Helpers
# # =========================
# def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
#     """
#     indices.pkl can be:
#     - dict(title -> index)
#     - pandas Series (index=title, value=index)
#     We normalize into TITLE_TO_IDX.
#     """
#     title_to_idx: Dict[str, int] = {}

#     if isinstance(indices, dict):
#         for k, v in indices.items():
#             title_to_idx[_norm_title(k)] = int(v)
#         return title_to_idx

#     # pandas Series or similar mapping
#     try:
#         for k, v in indices.items():
#             title_to_idx[_norm_title(k)] = int(v)
#         return title_to_idx
#     except Exception:
#         # last resort: if it's a list-like etc.
#         raise RuntimeError(
#             "indices.pkl must be dict or pandas Series-like (with .items())"
#         )


# def get_local_idx_by_title(title: str) -> int:
#     global TITLE_TO_IDX
#     if TITLE_TO_IDX is None:
#         raise HTTPException(status_code=500, detail="TF-IDF index map not initialized")
#     key = _norm_title(title)
#     if key in TITLE_TO_IDX:
#         return int(TITLE_TO_IDX[key])
#     raise HTTPException(
#         status_code=404, detail=f"Title not found in local dataset: '{title}'"
#     )


# def tfidf_recommend_titles(
#     query_title: str, top_n: int = 10
# ) -> List[Tuple[str, float]]:
#     """
#     Returns list of (title, score) from local df using cosine similarity on TF-IDF matrix.
#     Safe against missing columns/rows.
#     """
#     global df, tfidf_matrix
#     if df is None or tfidf_matrix is None:
#         raise HTTPException(status_code=500, detail="TF-IDF resources not loaded")

#     idx = get_local_idx_by_title(query_title)

#     # query vector
#     qv = tfidf_matrix[idx]
#     scores = (tfidf_matrix @ qv.T).toarray().ravel()

#     # sort descending
#     order = np.argsort(-scores)

#     out: List[Tuple[str, float]] = []
#     for i in order:
#         if int(i) == int(idx):
#             continue
#         try:
#             title_i = str(df.iloc[int(i)]["title"])
#         except Exception:
#             continue
#         out.append((title_i, float(scores[int(i)])))
#         if len(out) >= top_n:
#             break
#     return out


# async def attach_tmdb_card_by_title(title: str) -> Optional[TMDBMovieCard]:
#     """
#     Uses TMDB search by title to fetch poster for a local title.
#     If not found, returns None (never crashes the endpoint).
#     """
#     try:
#         m = await tmdb_search_first(title)
#         if not m:
#             return None
#         return TMDBMovieCard(
#             tmdb_id=int(m["id"]),
#             title=m.get("title") or title,
#             poster_url=make_img_url(m.get("poster_path")),
#             release_date=m.get("release_date"),
#             vote_average=m.get("vote_average"),
#         )
#     except Exception:
#         return None


# # =========================
# # STARTUP: LOAD PICKLES
# # =========================
# @app.on_event("startup")
# def load_pickles():
#     global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX

#     # Load df
#     with open(DF_PATH, "rb") as f:
#         df = pickle.load(f)

#     # Load indices
#     with open(INDICES_PATH, "rb") as f:
#         indices_obj = pickle.load(f)

#     # Load TF-IDF matrix (usually scipy sparse)
#     with open(TFIDF_MATRIX_PATH, "rb") as f:
#         tfidf_matrix = pickle.load(f)

#     # Load tfidf vectorizer (optional, not used directly here)
#     with open(TFIDF_PATH, "rb") as f:
#         tfidf_obj = pickle.load(f)

#     # Build normalized map
#     TITLE_TO_IDX = build_title_to_idx_map(indices_obj)

#     # sanity
#     if df is None or "title" not in df.columns:
#         raise RuntimeError("df.pkl must contain a DataFrame with a 'title' column")


# # =========================
# # ROUTES
# # =========================
# @app.get("/health")
# def health():
#     return {"status": "ok"}


# # ---------- HOME FEED (TMDB) ----------
# @app.get("/home", response_model=List[TMDBMovieCard])
# async def home(
#     category: str = Query("popular"),
#     limit: int = Query(24, ge=1, le=50),
# ):
#     """
#     Home feed for Streamlit (posters).
#     category:
#       - trending (trending/movie/day)
#       - popular, top_rated, upcoming, now_playing  (movie/{category})
#     """
#     try:
#         if category == "trending":
#             data = await tmdb_get("/trending/movie/day", {"language": "en-US"})
#             return await tmdb_cards_from_results(data.get("results", []), limit=limit)

#         if category not in {"popular", "top_rated", "upcoming", "now_playing"}:
#             raise HTTPException(status_code=400, detail="Invalid category")

#         data = await tmdb_get(f"/movie/{category}", {"language": "en-US", "page": 1})
#         return await tmdb_cards_from_results(data.get("results", []), limit=limit)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Home route failed: {e}")


# # ---------- TMDB KEYWORD SEARCH (MULTIPLE RESULTS) ----------
# @app.get("/tmdb/search")
# async def tmdb_search(
#     query: str = Query(..., min_length=1),
#     page: int = Query(1, ge=1, le=10),
# ):
#     """
#     Returns RAW TMDB shape with 'results' list.
#     Streamlit will use it for:
#       - dropdown suggestions
#       - grid results
#     """
#     return await tmdb_search_movies(query=query, page=page)


# # ---------- MOVIE DETAILS (SAFE ROUTE) ----------
# @app.get("/movie/id/{tmdb_id}", response_model=TMDBMovieDetails)
# async def movie_details_route(tmdb_id: int):
#     return await tmdb_movie_details(tmdb_id)


# # ---------- GENRE RECOMMENDATIONS ----------
# @app.get("/recommend/genre", response_model=List[TMDBMovieCard])
# async def recommend_genre(
#     tmdb_id: int = Query(...),
#     limit: int = Query(18, ge=1, le=50),
# ):
#     """
#     Given a TMDB movie ID:
#     - fetch details
#     - pick first genre
#     - discover movies in that genre (popular)
#     """
#     details = await tmdb_movie_details(tmdb_id)
#     if not details.genres:
#         return []

#     genre_id = details.genres[0]["id"]
#     discover = await tmdb_get(
#         "/discover/movie",
#         {
#             "with_genres": genre_id,
#             "language": "en-US",
#             "sort_by": "popularity.desc",
#             "page": 1,
#         },
#     )
#     cards = await tmdb_cards_from_results(discover.get("results", []), limit=limit)
#     return [c for c in cards if c.tmdb_id != tmdb_id]


# # ---------- TF-IDF ONLY (debug/useful) ----------
# @app.get("/recommend/tfidf")
# async def recommend_tfidf(
#     title: str = Query(..., min_length=1),
#     top_n: int = Query(10, ge=1, le=50),
# ):
#     recs = tfidf_recommend_titles(title, top_n=top_n)
#     return [{"title": t, "score": s} for t, s in recs]


# # ---------- BUNDLE: Details + TF-IDF recs + Genre recs ----------
# @app.get("/movie/search", response_model=SearchBundleResponse)
# async def search_bundle(
#     query: str = Query(..., min_length=1),
#     tfidf_top_n: int = Query(12, ge=1, le=30),
#     genre_limit: int = Query(12, ge=1, le=30),
# ):
#     """
#     This endpoint is for when you have a selected movie and want:
#       - movie details
#       - TF-IDF recommendations (local) + posters
#       - Genre recommendations (TMDB) + posters

#     NOTE:
#     - It selects the BEST match from TMDB for the given query.
#     - If you want MULTIPLE matches, use /tmdb/search
#     """
#     best = await tmdb_search_first(query)
#     if not best:
#         raise HTTPException(
#             status_code=404, detail=f"No TMDB movie found for query: {query}"
#         )

#     tmdb_id = int(best["id"])
#     details = await tmdb_movie_details(tmdb_id)

#     # 1) TF-IDF recommendations (never crash endpoint)
#     tfidf_items: List[TFIDFRecItem] = []

#     recs: List[Tuple[str, float]] = []
#     try:
#         # try local dataset by TMDB title
#         recs = tfidf_recommend_titles(details.title, top_n=tfidf_top_n)
#     except Exception:
#         # fallback to user query
#         try:
#             recs = tfidf_recommend_titles(query, top_n=tfidf_top_n)
#         except Exception:
#             recs = []

#     for title, score in recs:
#         card = await attach_tmdb_card_by_title(title)
#         tfidf_items.append(TFIDFRecItem(title=title, score=score, tmdb=card))

#     # 2) Genre recommendations (TMDB discover by first genre)
#     genre_recs: List[TMDBMovieCard] = []
#     if details.genres:
#         genre_id = details.genres[0]["id"]
#         discover = await tmdb_get(
#             "/discover/movie",
#             {
#                 "with_genres": genre_id,
#                 "language": "en-US",
#                 "sort_by": "popularity.desc",
#                 "page": 1,
#             },
#         )
#         cards = await tmdb_cards_from_results(
#             discover.get("results", []), limit=genre_limit
#         )
#         genre_recs = [c for c in cards if c.tmdb_id != details.tmdb_id]

#     return SearchBundleResponse(
#         query=query,
#         movie_details=details,
#         tfidf_recommendations=tfidf_items,
#         genre_recommendations=genre_recs,
#     )









# import os
# import pickle
# from contextlib import asynccontextmanager
# from typing import Optional, List, Dict, Any, Tuple

# import numpy as np
# import pandas as pd
# import httpx
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from dotenv import load_dotenv


# # =========================
# # ENV
# # =========================
# load_dotenv()
# TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# TMDB_BASE = "https://api.themoviedb.org/3"
# TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"

# if not TMDB_API_KEY:
#     raise RuntimeError("TMDB_API_KEY missing. Put it in .env as TMDB_API_KEY=xxxx")


# # =========================
# # PICKLE GLOBALS
# # =========================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DF_PATH = os.path.join(BASE_DIR, "df.pkl")
# INDICES_PATH = os.path.join(BASE_DIR, "indices.pkl")
# TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
# TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")

# df: Optional[pd.DataFrame] = None
# indices_obj: Any = None
# tfidf_matrix: Any = None
# tfidf_obj: Any = None

# TITLE_TO_IDX: Optional[Dict[str, int]] = None


# # =========================
# # MODELS
# # =========================
# class TMDBMovieCard(BaseModel):
#     tmdb_id: int
#     title: str
#     poster_url: Optional[str] = None
#     release_date: Optional[str] = None
#     vote_average: Optional[float] = None


# class TMDBMovieDetails(BaseModel):
#     tmdb_id: int
#     title: str
#     overview: Optional[str] = None
#     release_date: Optional[str] = None
#     poster_url: Optional[str] = None
#     backdrop_url: Optional[str] = None
#     genres: List[dict] = []


# class TFIDFRecItem(BaseModel):
#     title: str
#     score: float
#     tmdb: Optional[TMDBMovieCard] = None


# class SearchBundleResponse(BaseModel):
#     query: str
#     movie_details: TMDBMovieDetails
#     tfidf_recommendations: List[TFIDFRecItem]
#     genre_recommendations: List[TMDBMovieCard]


# # =========================
# # UTILS
# # =========================
# def _norm_title(t: str) -> str:
#     return str(t).strip().lower()


# def make_img_url(path: Optional[str]) -> Optional[str]:
#     if not path:
#         return None
#     return f"{TMDB_IMG_500}{path}"


# async def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
#     q = dict(params)
#     q["api_key"] = TMDB_API_KEY

#     try:
#         async with httpx.AsyncClient(timeout=20) as client:
#             r = await client.get(f"{TMDB_BASE}{path}", params=q)
#     except httpx.RequestError as e:
#         raise HTTPException(
#             status_code=502,
#             detail=f"TMDB request error: {type(e).__name__} | {repr(e)}",
#         )

#     if r.status_code != 200:
#         raise HTTPException(
#             status_code=502, detail=f"TMDB error {r.status_code}: {r.text}"
#         )

#     return r.json()


# async def tmdb_cards_from_results(
#     results: List[dict], limit: int = 20
# ) -> List[TMDBMovieCard]:
#     out: List[TMDBMovieCard] = []
#     for m in (results or [])[:limit]:
#         out.append(
#             TMDBMovieCard(
#                 tmdb_id=int(m["id"]),
#                 title=m.get("title") or m.get("name") or "",
#                 poster_url=make_img_url(m.get("poster_path")),
#                 release_date=m.get("release_date"),
#                 vote_average=m.get("vote_average"),
#             )
#         )
#     return out


# async def tmdb_movie_details(movie_id: int) -> TMDBMovieDetails:
#     data = await tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})
#     return TMDBMovieDetails(
#         tmdb_id=int(data["id"]),
#         title=data.get("title") or "",
#         overview=data.get("overview"),
#         release_date=data.get("release_date"),
#         poster_url=make_img_url(data.get("poster_path")),
#         backdrop_url=make_img_url(data.get("backdrop_path")),
#         genres=data.get("genres", []) or [],
#     )


# async def tmdb_search_movies(query: str, page: int = 1) -> Dict[str, Any]:
#     return await tmdb_get(
#         "/search/movie",
#         {
#             "query": query,
#             "include_adult": "false",
#             "language": "en-US",
#             "page": page,
#         },
#     )


# async def tmdb_search_first(query: str) -> Optional[dict]:
#     data = await tmdb_search_movies(query=query, page=1)
#     results = data.get("results", [])
#     return results[0] if results else None


# # =========================
# # TF-IDF Helpers
# # =========================
# def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
#     title_to_idx: Dict[str, int] = {}

#     if isinstance(indices, dict):
#         for k, v in indices.items():
#             title_to_idx[_norm_title(k)] = int(v)
#         return title_to_idx

#     try:
#         for k, v in indices.items():
#             title_to_idx[_norm_title(k)] = int(v)
#         return title_to_idx
#     except Exception:
#         raise RuntimeError(
#             "indices.pkl must be dict or pandas Series-like (with .items())"
#         )


# def get_local_idx_by_title(title: str) -> int:
#     global TITLE_TO_IDX
#     if TITLE_TO_IDX is None:
#         raise HTTPException(status_code=500, detail="TF-IDF index map not initialized")
#     key = _norm_title(title)
#     if key in TITLE_TO_IDX:
#         return int(TITLE_TO_IDX[key])
#     raise HTTPException(
#         status_code=404, detail=f"Title not found in local dataset: '{title}'"
#     )


# def tfidf_recommend_titles(
#     query_title: str, top_n: int = 10
# ) -> List[Tuple[str, float]]:
#     global df, tfidf_matrix
#     if df is None or tfidf_matrix is None:
#         raise HTTPException(status_code=500, detail="TF-IDF resources not loaded")

#     idx = get_local_idx_by_title(query_title)

#     qv = tfidf_matrix[idx]
#     scores = (tfidf_matrix @ qv.T).toarray().ravel()

#     order = np.argsort(-scores)

#     out: List[Tuple[str, float]] = []
#     for i in order:
#         if int(i) == int(idx):
#             continue
#         try:
#             title_i = str(df.iloc[int(i)]["title"])
#         except Exception:
#             continue
#         out.append((title_i, float(scores[int(i)])))
#         if len(out) >= top_n:
#             break
#     return out


# async def attach_tmdb_card_by_title(title: str) -> Optional[TMDBMovieCard]:
#     try:
#         m = await tmdb_search_first(title)
#         if not m:
#             return None
#         return TMDBMovieCard(
#             tmdb_id=int(m["id"]),
#             title=m.get("title") or title,
#             poster_url=make_img_url(m.get("poster_path")),
#             release_date=m.get("release_date"),
#             vote_average=m.get("vote_average"),
#         )
#     except Exception:
#         return None


# # =========================
# # STARTUP: LOAD PICKLES
# # ✅ FIXED: Using lifespan instead of deprecated @app.on_event("startup")
# # =========================
# def load_pickles():
#     global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX

#     print("Loading pickle files...")

#     if not os.path.exists(DF_PATH):
#         raise RuntimeError(f"df.pkl not found at {DF_PATH}")
#     if not os.path.exists(INDICES_PATH):
#         raise RuntimeError(f"indices.pkl not found at {INDICES_PATH}")
#     if not os.path.exists(TFIDF_MATRIX_PATH):
#         raise RuntimeError(f"tfidf_matrix.pkl not found at {TFIDF_MATRIX_PATH}")
#     if not os.path.exists(TFIDF_PATH):
#         raise RuntimeError(f"tfidf.pkl not found at {TFIDF_PATH}")

#     with open(DF_PATH, "rb") as f:
#         df = pickle.load(f)

#     with open(INDICES_PATH, "rb") as f:
#         indices_obj = pickle.load(f)

#     with open(TFIDF_MATRIX_PATH, "rb") as f:
#         tfidf_matrix = pickle.load(f)

#     with open(TFIDF_PATH, "rb") as f:
#         tfidf_obj = pickle.load(f)

#     TITLE_TO_IDX = build_title_to_idx_map(indices_obj)

#     if df is None or "title" not in df.columns:
#         raise RuntimeError("df.pkl must contain a DataFrame with a 'title' column")

#     print(f"✅ Loaded {len(df)} movies into TF-IDF index.")


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Runs on startup
#     load_pickles()
#     yield
#     # Runs on shutdown (nothing needed here)


# # =========================
# # FASTAPI APP
# # ✅ FIXED: lifespan passed here instead of @app.on_event
# # =========================
# app = FastAPI(title="Movie Recommender API", version="3.0", lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # =========================
# # ROUTES
# # =========================
# @app.get("/health")
# def health():
#     return {"status": "ok", "movies_loaded": len(df) if df is not None else 0}


# # ---------- HOME FEED (TMDB) ----------
# @app.get("/home", response_model=List[TMDBMovieCard])
# async def home(
#     category: str = Query("popular"),
#     limit: int = Query(24, ge=1, le=50),
# ):
#     try:
#         if category == "trending":
#             data = await tmdb_get("/trending/movie/day", {"language": "en-US"})
#             return await tmdb_cards_from_results(data.get("results", []), limit=limit)

#         if category not in {"popular", "top_rated", "upcoming", "now_playing"}:
#             raise HTTPException(status_code=400, detail="Invalid category")

#         data = await tmdb_get(f"/movie/{category}", {"language": "en-US", "page": 1})
#         return await tmdb_cards_from_results(data.get("results", []), limit=limit)

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Home route failed: {e}")


# # ---------- TMDB KEYWORD SEARCH ----------
# @app.get("/tmdb/search")
# async def tmdb_search(
#     query: str = Query(..., min_length=1),
#     page: int = Query(1, ge=1, le=10),
# ):
#     return await tmdb_search_movies(query=query, page=page)


# # ---------- MOVIE DETAILS ----------
# @app.get("/movie/id/{tmdb_id}", response_model=TMDBMovieDetails)
# async def movie_details_route(tmdb_id: int):
#     return await tmdb_movie_details(tmdb_id)


# # ---------- GENRE RECOMMENDATIONS ----------
# @app.get("/recommend/genre", response_model=List[TMDBMovieCard])
# async def recommend_genre(
#     tmdb_id: int = Query(...),
#     limit: int = Query(18, ge=1, le=50),
# ):
#     details = await tmdb_movie_details(tmdb_id)
#     if not details.genres:
#         return []

#     genre_id = details.genres[0]["id"]
#     discover = await tmdb_get(
#         "/discover/movie",
#         {
#             "with_genres": genre_id,
#             "language": "en-US",
#             "sort_by": "popularity.desc",
#             "page": 1,
#         },
#     )
#     cards = await tmdb_cards_from_results(discover.get("results", []), limit=limit)
#     return [c for c in cards if c.tmdb_id != tmdb_id]


# # ---------- TF-IDF ONLY ----------
# @app.get("/recommend/tfidf")
# async def recommend_tfidf(
#     title: str = Query(..., min_length=1),
#     top_n: int = Query(10, ge=1, le=50),
# ):
#     recs = tfidf_recommend_titles(title, top_n=top_n)
#     return [{"title": t, "score": s} for t, s in recs]


# # ---------- BUNDLE: Details + TF-IDF + Genre ----------
# @app.get("/movie/search", response_model=SearchBundleResponse)
# async def search_bundle(
#     query: str = Query(..., min_length=1),
#     tfidf_top_n: int = Query(12, ge=1, le=30),
#     genre_limit: int = Query(12, ge=1, le=30),
# ):
#     best = await tmdb_search_first(query)
#     if not best:
#         raise HTTPException(
#             status_code=404, detail=f"No TMDB movie found for query: {query}"
#         )

#     tmdb_id = int(best["id"])
#     details = await tmdb_movie_details(tmdb_id)

#     tfidf_items: List[TFIDFRecItem] = []
#     recs: List[Tuple[str, float]] = []

#     try:
#         recs = tfidf_recommend_titles(details.title, top_n=tfidf_top_n)
#     except Exception:
#         try:
#             recs = tfidf_recommend_titles(query, top_n=tfidf_top_n)
#         except Exception:
#             recs = []

#     for title, score in recs:
#         card = await attach_tmdb_card_by_title(title)
#         tfidf_items.append(TFIDFRecItem(title=title, score=score, tmdb=card))

#     genre_recs: List[TMDBMovieCard] = []
#     if details.genres:
#         genre_id = details.genres[0]["id"]
#         discover = await tmdb_get(
#             "/discover/movie",
#             {
#                 "with_genres": genre_id,
#                 "language": "en-US",
#                 "sort_by": "popularity.desc",
#                 "page": 1,
#             },
#         )
#         cards = await tmdb_cards_from_results(
#             discover.get("results", []), limit=genre_limit
#         )
#         genre_recs = [c for c in cards if c.tmdb_id != details.tmdb_id]

#     return SearchBundleResponse(
#         query=query,
#         movie_details=details,
#         tfidf_recommendations=tfidf_items,
#         genre_recommendations=genre_recs,
#     )












import requests
import streamlit as st

# =============================
# CONFIG
# ✅ FIXED: Use environment variable for API base URL
#    Set BACKEND_URL in Render environment variables
#    For local dev it falls back to localhost
# =============================
import os
API_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")

# =============================
# STYLES
# =============================
st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
.small-muted { color:#6b7280; font-size: 0.92rem; }
.movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
.card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# STATE + ROUTING
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except Exception:
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
    st.query_params["id"] = str(int(tmdb_id))
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=25)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Cannot connect to backend at {API_BASE}. Is the backend service running?"
    except requests.exceptions.Timeout:
        return None, "Request timed out. Backend may be starting up — please wait and retry."
    except Exception as e:
        return None, f"Request failed: {e}"


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1

            tmdb_id = m.get("tmdb_id")
            title = m.get("title", "Untitled")
            poster = m.get("poster_url")

            with colset[c]:
                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.write("🖼️ No poster")

                if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}_{tmdb_id}"):
                    if tmdb_id:
                        goto_details(tmdb_id)

                st.markdown(
                    f"<div class='movie-title'>{title}</div>", unsafe_allow_html=True
                )


def to_cards_from_tfidf_items(tfidf_items):
    cards = []
    for x in tfidf_items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append(
                {
                    "tmdb_id": tmdb["tmdb_id"],
                    "title": tmdb.get("title") or x.get("title") or "Untitled",
                    "poster_url": tmdb.get("poster_url"),
                }
            )
    return cards


def parse_tmdb_search_to_cards(data, keyword: str, limit: int = 24):
    keyword_l = keyword.strip().lower()

    if isinstance(data, dict) and "results" in data:
        raw = data.get("results") or []
        raw_items = []
        for m in raw:
            title = (m.get("title") or "").strip()
            tmdb_id = m.get("id")
            poster_path = m.get("poster_path")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": f"{TMDB_IMG}{poster_path}" if poster_path else None,
                    "release_date": m.get("release_date", ""),
                }
            )

    elif isinstance(data, list):
        raw_items = []
        for m in data:
            tmdb_id = m.get("tmdb_id") or m.get("id")
            title = (m.get("title") or "").strip()
            poster_url = m.get("poster_url")
            if not title or not tmdb_id:
                continue
            raw_items.append(
                {
                    "tmdb_id": int(tmdb_id),
                    "title": title,
                    "poster_url": poster_url,
                    "release_date": m.get("release_date", ""),
                }
            )
    else:
        return [], []

    matched = [x for x in raw_items if keyword_l in x["title"].lower()]
    final_list = matched if matched else raw_items

    suggestions = []
    for x in final_list[:10]:
        year = (x.get("release_date") or "")[:4]
        label = f"{x['title']} ({year})" if year else x["title"]
        suggestions.append((label, x["tmdb_id"]))

    cards = [
        {"tmdb_id": x["tmdb_id"], "title": x["title"], "poster_url": x["poster_url"]}
        for x in final_list[:limit]
    ]
    return suggestions, cards


# =============================
# BACKEND HEALTH CHECK
# ✅ NEW: Shows a warning if backend is unreachable
# =============================
def check_backend_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=10)
        if r.status_code == 200:
            return True, r.json()
        return False, f"Backend returned HTTP {r.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Backend unreachable"
    except requests.exceptions.Timeout:
        return False, "Backend timed out (may be starting up)"
    except Exception as e:
        return False, str(e)


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("## 🎬 Menu")
    if st.button("🏠 Home"):
        goto_home()

    st.markdown("---")

    # ✅ NEW: Show backend connection status in sidebar
    st.markdown("### 🔌 Backend Status")
    ok, info = check_backend_health()
    if ok:
        movies_loaded = info.get("movies_loaded", "?") if isinstance(info, dict) else "?"
        st.success(f"Connected ✅ ({movies_loaded} movies)")
    else:
        st.error(f"Disconnected ❌\n{info}")
        st.caption(f"Backend URL: `{API_BASE}`")

    st.markdown("---")
    st.markdown("### 🏠 Home Feed")
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
        index=0,
    )
    grid_cols = st.slider("Grid columns", 4, 8, 6)


# =============================
# HEADER
# =============================
st.title("🎬 Movie Recommender")
st.markdown(
    "<div class='small-muted'>Type keyword → dropdown suggestions + matching results → open → details + recommendations</div>",
    unsafe_allow_html=True,
)
st.divider()

# ==========================================================
# VIEW: HOME
# ==========================================================
if st.session_state.view == "home":
    typed = st.text_input(
        "Search by movie title (keyword)", placeholder="Type: avenger, batman, love..."
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
                suggestions, cards = parse_tmdb_search_to_cards(
                    data, typed.strip(), limit=24
                )

                if suggestions:
                    labels = ["-- Select a movie --"] + [s[0] for s in suggestions]
                    selected = st.selectbox("Suggestions", labels, index=0)

                    if selected != "-- Select a movie --":
                        label_to_id = {s[0]: s[1] for s in suggestions}
                        goto_details(label_to_id[selected])
                else:
                    st.info("No suggestions found. Try another keyword.")

                st.markdown("### Results")
                poster_grid(cards, cols=grid_cols, key_prefix="search_results")

        st.stop()

    # HOME FEED
    st.markdown(f"### 🏠 Home — {home_category.replace('_',' ').title()}")

    home_cards, err = api_get_json(
        "/home", params={"category": home_category, "limit": 24}
    )
    if err or not home_cards:
        st.error(f"Home feed failed: {err or 'Unknown error'}")

        # ✅ NEW: Helpful tip when backend is down
        if not ok:
            st.warning(
                "💡 Your backend service may be sleeping (Render free tier). "
                "Visit your backend URL once to wake it up, then refresh this page."
            )
        st.stop()

    poster_grid(home_cards, cols=grid_cols, key_prefix="home_feed")

# ==========================================================
# VIEW: DETAILS
# ==========================================================
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
        genres = ", ".join([g["name"] for g in data.get("genres", [])]) or "-"
        st.markdown(
            f"<div class='small-muted'>Release: {release}</div>", unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='small-muted'>Genres: {genres}</div>", unsafe_allow_html=True
        )
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
                cols=grid_cols,
                key_prefix="details_tfidf",
            )

            st.markdown("#### 🎭 More Like This (Genre)")
            poster_grid(
                bundle.get("genre_recommendations", []),
                cols=grid_cols,
                key_prefix="details_genre",
            )
        else:
            st.info("Showing Genre recommendations (fallback).")
            genre_only, err3 = api_get_json(
                "/recommend/genre", params={"tmdb_id": tmdb_id, "limit": 18}
            )
            if not err3 and genre_only:
                poster_grid(
                    genre_only, cols=grid_cols, key_prefix="details_genre_fallback"
                )
            else:
                st.warning("No recommendations available right now.")
    else:
        st.warning("No title available to compute recommendations.")