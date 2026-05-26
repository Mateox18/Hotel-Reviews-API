import os
from datetime import date, datetime, time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from dotenv import load_dotenv

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False
)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
if MONGO_URI is None:
    raise RuntimeError("Falta MONGO_URI en el archivo .env")

if MONGO_DB_NAME is None:
    raise RuntimeError("Falta MONGO_DB_NAME en el archivo .env")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db["resenas"]

@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}

@app.get("/resenas/top10")
def obtener_resenas(fecha_inicio: date, fecha_fin: date):
    inicio = datetime.combine(fecha_inicio, time.min)
    fin = datetime.combine(fecha_fin, time.max)

    pipeline = [
        {
            "$match": {
                "fechaCreacion": {
                    "$gte": inicio,
                    "$lte": fin,
                },
                "estado": "publicada",
            }
        },
        {
            "$group": {
                "_id": "$idHotel",
                "promedioCalificacion": {
                    "$avg": "$calificacion"
                },
                "totalResenas": {
                    "$sum": 1
                },
            }
        },
        {
            "$sort": {
                "promedioCalificacion": -1
            }
        },
        {
            "$limit": 10
        },
    ]
    resultado = list(collection.aggregate(pipeline))
    return resultado

@app.get("/resenas/evoanio")
def evo_anio(anio:int, id_hotel:int):
    pipeline = [
        {
            "$match": {
                "idHotel": id_hotel,
                "estado": "publicada",
                "fechaCreacion": {
                    "$gte": datetime(anio, 1, 1),
                    "$lt": datetime(anio + 1, 1, 1)
                }
            }
        },

        {
            "$group": {
                "_id": {
                    "mes": {
                        "$month": "$fechaCreacion"
                    }
                },

                "promedioMensual": {
                    "$avg": "$calificacion"
                },

                "cantidadResenas": {
                    "$sum": 1
                }
            }
        },

        {
            "$project": {
                "_id": 0,

                "mes": "$_id.mes",

                "promedioMensual": {
                    "$round": ["$promedioMensual", 2]
                },

                "cantidadResenas": 1
            }
        }
    ]
    resultado = list(collection.aggregate(pipeline))
    return resultado
@app.get("/resenas/comphotel")
def comphotel():
    pipeline = [
        {
            "$match": {
                "estado": "publicada"
            }
        },

        {
            "$group": {
                "_id": "$idHotel",

                "promedioGeneral": {
                    "$avg": "$calificacion"
                },

                "totalResenas": {
                    "$sum": 1
                },

                "respuestasAdmin": {
                    "$sum": {
                        "$cond": [
                            {
                                "$ne": ["$respuestaAdmin", None]
                            },
                            1,
                            0
                        ]
                    }
                },

                "destacadas": {
                    "$sum": {
                        "$cond": [
                            {
                                "$eq": ["$destacada", True]
                            },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]
    resultado = list(collection.aggregate(pipeline))
    return resultado


