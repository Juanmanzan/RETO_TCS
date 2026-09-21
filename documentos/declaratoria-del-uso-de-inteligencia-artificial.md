# Declaratoria del Uso de Inteligencia Artificial

## Proposito

Durante el desarrollo del reto tecnico se utilizaron herramientas de inteligencia artificial como apoyo para acelerar actividades de analisis, estructuracion, documentacion y validacion tecnica. El uso de estas herramientas fue complementario y no reemplazo la toma de decisiones, implementacion, configuracion ni validacion final realizada por el candidato.

## Herramientas Utilizadas

- ChatGPT: utilizado como asistente de apoyo para analisis tecnico, revision de codigo, organizacion de ideas y validacion de escenarios de prueba.

## Forma de Uso

La inteligencia artificial se empleo como herramienta de asistencia para:

- Analizar alternativas de arquitectura y ayudar a estructurar la explicacion tecnica del sistema.
- Apoyar la identificacion de patrones utilizados en la solucion, como separacion por capas, composicion de servicios, adaptadores de infraestructura y procesamiento asincrono basado en eventos.
- Revisar posibles causas de errores durante la ejecucion local, especialmente en integracion entre API, Redis, MQTT y PostgreSQL.
- Apoyar el analisis de resultados de k6, metricas de contenedores y comportamiento bajo carga.
- Revisar configuraciones relacionadas con Docker Compose, observabilidad, logs, metricas y workers.

## Componentes Donde se Aplico

### Arquitectura General

Se utilizo IA para apoyar la organizacion conceptual de la arquitectura, la descripcion de los componentes principales y la explicacion del flujo general entre API de transacciones, Redis, MQTT, workers, PostgreSQL, API de IA y herramientas de observabilidad.

### API de Transacciones

Se empleó IA para explorar alternativas que garanticen transacciones rápidas, atómicas y libres de race conditions.

### Worker Publicador de Eventos

Se utilizo IA para apoyar el analisis y validacion del flujo de eventos desde Redis Stream hacia MQTT.

### Worker de Persistencia

Se utilizó IA para revisar el proceso de persistencia en PostgreSQL, validar y contrastar que las transacciones se realicen de forma efectiva. Asimismo, se empleó con el propósito de detectar posibles cuellos de botella


### Observabilidad y Operacion

Se utilizó IA para estructurar validar las métricas expuestas en Grafana/VictoriaMetrics, verificando y contrastando que los datos mostrados reflejen un comportamiento real del sistema frente a la carga de trabajo.

### Pruebas de Carga y Validacion

Se utilizó IA para apoyar la interpretación de resultados de k6, el análisis de latencia, throughput, errores y saturación de recursos, identificando posibles fallos en la arquitectura que limitan el número de transacciones por minuto y permitiendo formular recomendaciones de ajuste en la arquitectura planteada.



## Alcance y Responsabilidad

El uso de inteligencia artificial se limito a actividades de apoyo, analisis y revision tecnica. Las decisiones finales de diseno, implementacion, pruebas, configuracion y validacion del reto fueron realizadas por el candidato.

El codigo, configuraciones, pruebas y entregables incluidos en el repositorio fueron revisados y validados en el entorno local antes de su entrega.

