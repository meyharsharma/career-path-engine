from fastapi import FastAPI

app = FastAPI( 
    title='Career Path Recommendation Engine API',
    version='0.1.0'
)

@app.get('/')
def root():
    return {'message': 'Backend API is running'}