import os
from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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


class CrearResena(BaseModel):
    idReserva: int
    idHotel: int
    idCliente: int
    calificacion: int = Field(ge=1, le=5)
    comentario: str
    destacada: bool = False


class EditarResena(BaseModel):
    calificacion: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = None
    destacada: Optional[bool] = None
    estado: Optional[str] = None


class RespuestaAdmin(BaseModel):
    idAdmin: int
    texto: str


class MarcarUtilidad(BaseModel):
    idCliente: int


@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}
#Requerimientos de consulta
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
@app.get("/resenas/hotel/{id_hotel}")
def hotel(id_hotel:int):
    resenas = list(collection.find({"idHotel": id_hotel}, {"_id": 0}))

    return {
        "idHotel": id_hotel,
        "total": len(resenas),
        "resenas": resenas
    }
@app.get("/resenas/cliente/{id_cliente}")
def cliente(id_cliente:int):
    cliente = list(collection.find({"idCliente": id_cliente}, {"_id": 0}))
    return {
        "idCliente": id_cliente,
        "total": len(cliente),
        "resenas": cliente
    }
@app.get("/resenas/reserva/{id_reserva}")
def obtener_resena_por_reserva(id_reserva: int):
    resena = collection.find_one(
        {"idReserva": id_reserva},
        {"_id": 0}
    )

    if resena is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontro una resena con ese idReserva"
        )

    return {
        "idReserva": id_reserva,
        "resena": resena
    }
@app.get("/resenas/{id_reserva}")
def reserva(id_reserva: int):
    resena = collection.find_one({"idReserva": id_reserva}, {"_id": 0})

    if resena is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontro una resena con ese idReserva"
        )

    return {
        "idReserva": id_reserva,
        "resena": resena
    }
#Requerimientos funcionales
@app.post("/resenas")
def crear_resena(resena: CrearResena):
    if collection.find_one({"idReserva": resena.idReserva}) is not None:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una resena con ese idReserva"
        )
    fecha_actual = datetime.now(timezone.utc)

    nueva_resena = {
        "idReserva": resena.idReserva,
        "idHotel": resena.idHotel,
        "idCliente": resena.idCliente,
        "calificacion": resena.calificacion,
        "comentario": resena.comentario,
        "fechaCreacion": fecha_actual,
        "fechaActualizacion": fecha_actual,
        "estado": "publicada",
        "destacada": resena.destacada,
        "utilidad": {
            "cantidad": 0,
            "usuarios": []
        },
        "respuestaAdmin": None
    }

    resultado = collection.insert_one(nueva_resena)

    return {
        "mensaje": "Resena creada correctamente",
        "id": str(resultado.inserted_id)
    }

@app.patch("/resenas/{id_reserva}")
def editar_resena(id_reserva: int, datos: EditarResena):
    cambios = datos.model_dump(exclude_unset=True)

    if len(cambios) == 0:
        raise HTTPException(
            status_code=400,
            detail="No se enviaron campos validos para actualizar"
        )

    cambios["fechaActualizacion"] = datetime.now(timezone.utc)

    resultado = collection.update_one(
        {"idReserva": id_reserva},
        {"$set": cambios}
    )

    if resultado.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontro una resena con ese idReserva"
        )

    return {
        "mensaje": "Resena actualizada correctamente",
        "idReserva": id_reserva,
        "camposActualizados": [
            campo for campo in cambios.keys()
            if campo != "fechaActualizacion"
        ]
    }

@app.delete("/resenas/{id_reserva}")
def eliminar_resena(id_reserva: int):
    resultado = collection.delete_one({"idReserva": id_reserva})

    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontro una resena con ese idReserva"
        )

    return {
        "mensaje": "Resena eliminada correctamente",
        "idReserva": id_reserva
    }
@app.patch("/resenas/{id_reserva}/responder_admin")
def responder_admin(id_reserva: int, datos: RespuestaAdmin):
    respuesta_admin = {
        "idAdmin": datos.idAdmin,
        "texto": datos.texto,
        "fechaRespuesta": datetime.now(timezone.utc)
    }

    resultado = collection.update_one(
        {"idReserva": id_reserva},
        {
            "$set": {
                "respuestaAdmin": respuesta_admin,
                "fechaActualizacion": datetime.now(timezone.utc)
            }
        }
    )

    if resultado.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontro una resena con ese idReserva"
        )

    return {
        "mensaje": "Respuesta del admin guardada correctamente",
        "idReserva": id_reserva,
        "respuestaAdmin": respuesta_admin
    }
@app.patch("/resenas/{id_reserva}/destacar_admin")
def destacar_admin(id_reserva: int):
    resultado = collection.update_one(
        {"idReserva": id_reserva},
        {
            "$set": {
                "destacada": True,
                "fechaActualizacion": datetime.now(timezone.utc)
            }
        }
    )

    if resultado.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontro una resena con ese idReserva"
        )

    return {
        "mensaje": "Resena destacada correctamente",
        "idReserva": id_reserva,
        "destacada": True
    }

@app.patch("/resenas/{id_reserva}/utilidad")
def marcar_utilidad(id_reserva: int, datos: MarcarUtilidad):
    id_cliente = datos.idCliente

    resultado = collection.update_one(
        {
            "idReserva": id_reserva,
            "utilidad.usuarios": {"$ne": id_cliente}
        },
        {
            "$inc": {
                "utilidad.cantidad": 1
            },
            "$addToSet": {
                "utilidad.usuarios": id_cliente
            },
            "$set": {
                "fechaActualizacion": datetime.now(timezone.utc)
            }
        }
    )

    if resultado.matched_count == 0:
        resena = collection.find_one({"idReserva": id_reserva})

        if resena is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontro una resena con ese idReserva"
            )

        raise HTTPException(
            status_code=400,
            detail="Este cliente ya marco la resena como util"
        )

    return {
        "mensaje": "Utilidad registrada correctamente",
        "idReserva": id_reserva,
        "idCliente": id_cliente
    }
