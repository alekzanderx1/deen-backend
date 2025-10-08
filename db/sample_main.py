from fastapi import FastAPI
from db.session import engine, Base
from routers import lessons as lessons_router
from routers import lesson_content as lesson_content_router
from routers import user_progress as user_progress_router
from routers import users as users_router
from routers import hikmah_trees as hikmah_trees_router

app = FastAPI(title="DeenAI Minimal CRUD API", version="1.0.0")

# (Optional) dev only — create tables if they don't exist
# Base.metadata.create_all(bind=engine)

# Register routers
app.include_router(lessons_router.router)
app.include_router(lesson_content_router.router)
app.include_router(user_progress_router.router)
app.include_router(users_router.router)
app.include_router(hikmah_trees_router.router)
