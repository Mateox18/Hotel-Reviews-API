REST API developed with FastAPI and MongoDB to analyze hotel reviews and generate business metrics.

## Tech Stack

- Python
- FastAPI
- MongoDB
- PyMongo
- REST APIs

## Features

- Retrieve hotel reviews
- Create new reviews
- Generate rating averages
- Analyze monthly review trends
- Compare hotels using aggregation pipelines

## API Endpoints

GET /resenas/comphotel
GET /resenas/hotel/{id}
GET /resenas/hotel/{id}/mensual

## Setup

1. Clone the repository
2. Create a virtual environment
3. Install dependencies
4. Create a .env file
5. Run the API with uvicorn

## Example

```bash
uvicorn main:app --reload
