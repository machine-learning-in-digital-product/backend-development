from fastapi import FastAPI
from routers.predictions import router as prediction_router
import uvicorn

app = FastAPI()
app.include_router(prediction_router)

@app.get("/")
async def root():
    return {'message': 'Hello World'}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
