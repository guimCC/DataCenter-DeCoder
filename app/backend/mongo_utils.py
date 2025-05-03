import pymongo

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

def insert_modules(modules):
    db = get_database()
    collection = db.modules
    result = collection.insert_many(modules)
    return result.inserted_ids

def get_all_modules():
    db = get_database()
    collection = db.modules
    return list(collection.find({}, {"_id": 0}))

# Para probar la conexión cuando se ejecuta este archivo directamente
if __name__ == "__main__":
    test_connection()