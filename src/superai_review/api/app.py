from fastapi import FastAPI

from superai_review import __version__

app = FastAPI(
    title="SuperAI.review",
    version=__version__,
    description="Multi-model review and synthesis platform.",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "SuperAI.review",
        "tagline": "Ask once. Let AI argue. Get the best answer.",
        "version": __version__,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "superai.review", "version": __version__}
