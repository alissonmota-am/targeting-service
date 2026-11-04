"""
Inicializacao do OpenTelemetry para o targeting-service (traces + metricas).

Configura os providers de traces e metricas e conecta ao OTel Collector
via OTLP/gRPC. A instrumentacao automatica de Flask, requests e psycopg2
cria spans e a metrica http.server.duration (ms, atributo http.status_code)
sem alterar o codigo das rotas.

O RequestsInstrumentor propaga o header traceparent nas chamadas ao
auth-service, garantindo o trace distribuido.
"""
import os
import logging

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

log = logging.getLogger(__name__)


def init_telemetry(app):
    """ Inicializa o OpenTelemetry e instrumenta Flask, requests e psycopg2. """
    service_name = os.getenv("OTEL_SERVICE_NAME", "targeting-service")
    environment = os.getenv("DEPLOYMENT_ENVIRONMENT", "dev")
    # endpoint do OTel Collector; gRPC na porta 4317
    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "otel-collector.observability.svc.cluster.local:4317",
    )

    try:
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: "1.0.0",
            DEPLOYMENT_ENVIRONMENT: environment,
        })

        # insecure=True porque a comunicacao com o Collector e interna ao cluster
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
        trace.set_tracer_provider(provider)

        # Metricas: o MeterProvider deve ser definido ANTES de instrumentar,
        # pois os instrumentors obtem o meter do provider global.
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint, insecure=True),
            export_interval_millis=15000,
        )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

        # Instrumentacao automatica — nao altera as rotas existentes
        FlaskInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()
        Psycopg2Instrumentor().instrument()

        log.info(f"[OTel] Telemetria (traces + metricas) inicializada — servico: {service_name}, endpoint: {endpoint}")
    except Exception as e:
        # Falha na telemetria nao deve impedir o servico de subir
        log.warning(f"[OTel] Nao foi possivel inicializar a telemetria: {e}")
