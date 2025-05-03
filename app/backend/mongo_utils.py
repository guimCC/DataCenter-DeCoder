import pymongo
import pandas as pd

# Conexión hardcodeada a MongoDB Atlas
MONGO_URI = "mongodb+srv://decoder:decoder@cluster0.dniasbm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def get_database():
    """Conecta a MongoDB y devuelve la base de datos"""
    client = pymongo.MongoClient(MONGO_URI)
    return client.datacenter_db  # Nombre de la base de datos

def test_connection():
    """Prueba la conexión a MongoDB"""
    try:
        db = get_database()
        # Ejecuta un comando simple para verificar la conexión
        db.command('ping')
        print("✅ Conexión a MongoDB establecida correctamente!")
        return True
    except Exception as e:
        print(f"❌ Error al conectar a MongoDB: {e}")
        return False

# Para probar la conexión cuando se ejecuta este archivo directamente
if __name__ == "__main__":
    test_connection()