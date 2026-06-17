# Diccionario de reglas del recomendador

Este documento describe la lógica utilizada para recomendar maestrías UDLA a graduados de pregrado.

## Objetivo

Generar un Top 3 de maestrías sugeridas por graduado, considerando su perfil académico y su trayectoria laboral.

## Variables utilizadas

El modelo utiliza las siguientes variables:

- Carrera de pregrado.
- Facultad de pregrado.
- Título obtenido.
- Fecha de graduación.
- Tipo de empresa.
- Nombre de empresa.
- Cargo u ocupación.
- Fecha de ingreso al cargo.
- Años en el cargo.
- Catálogo de maestrías UDLA.

## Fuentes de información

### Excel de graduados

Contiene la información académica del graduado.

Campos principales:

- Identificador
- Estudiante
- CarreraHom
- desfacultad
- Titulo
- FechaGraduacion
- Modalidad

### SQL Server

Tabla laboral:

```sql
[Reportes].[dbo].[SIM_Y_ENE_26]
