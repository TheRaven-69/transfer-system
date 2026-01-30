from fastapi import FastAPI


app =FastAPI(title="Transfer System API")


@app.get("/")
def root():
    return {"status": "ok"}


