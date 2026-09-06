"""Los dos servicios, el emisor y las piezas de instrumento de PL-2.

Aqui NO viven las reglas de cadena de frio. Viven en `banco/`, y SV-1 las
importa. Una segunda implementacion de RC-01...RC-12 seria la regla escrita dos
veces con media viva, que es el defecto que la mutacion estricta encontro en P4.

Lo que este paquete anade sobre el banco es todo lo que el banco no tiene por
diseno: persistencia, frontera entre dos almacenes, transporte y arranque.
"""
