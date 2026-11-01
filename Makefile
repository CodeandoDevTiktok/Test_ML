# Atajos (Linux/macOS). En Windows use directamente: python tareas.py <comando>
# La URL de GitHub NO va aquí: está en proyecto.yaml -> github.url
PY ?= python
MSG ?= "actualización"
TAG ?= datos-v1
N ?= 40

.PHONY: estado setup datos repro guardar publicar version e3 e4 e5 todo verificar test minio
estado:   ; $(PY) tareas.py estado
setup:    ; $(PY) tareas.py setup
datos:    ; $(PY) tareas.py descargar && $(PY) tareas.py registrar-crudo
repro e3: ; $(PY) tareas.py repro
guardar:  ; $(PY) tareas.py guardar -m $(MSG)
publicar: ; $(PY) tareas.py publicar
version:  ; $(PY) tareas.py version-datos $(TAG) -m $(MSG)
e4:       ; $(PY) tareas.py e4 --n-trials $(N)
e5:       ; $(PY) tareas.py e5
todo: repro e4 e5
verificar:; $(PY) tareas.py verificar
test:     ; $(PY) -m pytest -q
minio:    ; $(PY) tareas.py minio-listar
