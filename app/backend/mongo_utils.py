from numpy import delete
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

def delete_modules_by_id_greater_than(threshold_id):
    """Deletes modules from the database where ID is greater than the threshold."""
    try:
        db = get_database()
        collection = db.modules
        # Assuming the field name for the ID is 'ID'
        query = {"id": {"$gt": threshold_id}}
        result = collection.delete_many(query)
        return result.deleted_count
    except Exception as e:
        return 0


# Para probar la conexión cuando se ejecuta este archivo directamente
if __name__ == "__main__":
    test_connection()
    # delete_modules_by_id_greater_than(19)
    all_modules = get_all_modules()
    ids = {module['id'] for module in all_modules if 'id' in module}
    print(ids)
