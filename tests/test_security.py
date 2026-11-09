from app.errors import enmascarar
from app.security import hasher, puede, resumir_token, verificar_clave


def test_contrasenas_y_hash_de_sesion():
    hash_clave = hasher.hash("una contraseña de prueba")
    assert verificar_clave("una contraseña de prueba", hash_clave)
    assert not verificar_clave("incorrecta", hash_clave)
    assert not verificar_clave("incorrecta", "hash inválido")
    assert resumir_token("token") != "token"
    assert len(resumir_token("token")) == 64


def test_permisos_denegacion_por_defecto():
    assert puede("admin", "reglas")
    assert puede("gestor_anuncios", "bandeja")
    assert not puede("gestor_anuncios", "reglas")
    assert not puede("gestor_anuncios", "agentes")
    assert not puede("intruso", "solicitudes")


def test_datos_enmascarados():
    texto = enmascarar("Contacto persona@empresa.co +573001234567")
    assert "persona@empresa.co" not in texto
    assert "3001234567" not in texto
