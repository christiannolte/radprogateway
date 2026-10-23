# radprogateway

Liest einen Geigerzähler über die serielle Schnittstelle aus (`GET tubeRate`, `GET tubePulseCount`, `GET tubeSensitivity`) und veröffentlicht die Messwerte per MQTT.

- `<TOPIC>/data` – JSON mit Dosisleistung, Aktivität, Sensitivität, Min/Max (alle 60 s)
- `<TOPIC>/status` – `online` / `offline` (Last Will, retained)

## Konfiguration (Umgebungsvariablen)

Es gibt keine Defaults im Code. Fehlt eine Pflichtvariable, beendet sich das Programm mit einer Fehlermeldung.

| Variable      | Pflicht | Beschreibung                                    |
|---------------|---------|-------------------------------------------------|
| `BROKER`      | ja      | MQTT-Broker (Hostname)                          |
| `TOPIC`       | ja      | Topic-Präfix                                    |
| `SERIAL_PORT` | ja      | Serielle Schnittstelle, z. B. `/dev/ttyUSB0`    |
| `MQTT_PORT`   | nein    | MQTT-Port, Standard `1883`                      |

Lokal:

```bash
pip install -r requirements.txt
BROKER=mqtt.example.org TOPIC=mein/topic SERIAL_PORT=/dev/ttyUSB0 python src/radprogateway.py
```

## Docker-Image

Das Image `docker.io/christiannolte/radprogateway` wird von der GitHub Action (`.github/workflows/docker.yml`) bei jedem Push auf `main` gebaut und nach Docker Hub gepusht. Im Repo muss dafür das Secret `DOCKER_HUB_TOKEN` gesetzt sein.

```bash
docker run --rm --device /dev/ttyUSB0 \
  -e BROKER=mqtt.example.org -e TOPIC=mein/topic -e SERIAL_PORT=/dev/ttyUSB0 \
  docker.io/christiannolte/radprogateway:latest
```

## Kubernetes / ArgoCD

Das Helm-Chart liegt in `deploy/radprogateway`. In `values.yaml` stehen nur Dummy-Werte (`CHANGE_ME`) – die echten Werte werden erst in ArgoCD gesetzt, damit nichts davon im öffentlichen Repo steht.

### 1. Node vorbereiten

Das Messgerät hängt per USB/seriell an einem bestimmten Node. Der Pod ist deshalb per `nodeSelector` auf Nodes mit dem Label `radprogateway/serial=true` festgelegt. Ohne dieses Label bleibt der Pod im Status `Pending`.

`<node-name>` ist der Name des Nodes, an dem das Messgerät angeschlossen ist (Spalte `NAME`):

```bash
kubectl get nodes
kubectl label node <node-name> radprogateway/serial=true
```

Kontrolle:

```bash
kubectl get nodes -l radprogateway/serial=true
```

Auf dem Node muss das Gerät vorhanden sein (Pfad = `SERIAL_PORT`):

```bash
ls -l /dev/ttyUSB0    # bzw. /dev/ttyS0 o. ä.
```

Der Container läuft `privileged`, damit er die Host-Geräte unter `/dev` sieht. Es wird kein `hostPath`-Volume gemountet; der Pfad aus `SERIAL_PORT` muss daher im Container unter `/dev` existieren. Es darf nur ein Pod gleichzeitig auf das Gerät zugreifen (Deployment-Strategie `Recreate`, 1 Replikat).

### 2. Application in ArgoCD anlegen

Entweder `argocd/application.yaml` anpassen und anwenden:

```bash
kubectl apply -f argocd/application.yaml
```

Dabei die `CHANGE_ME`-Werte unter `spec.source.helm.valuesObject.config` ersetzen (nicht ins öffentliche Repo committen), oder die Application in der ArgoCD-Oberfläche anlegen und die Helm-Parameter dort setzen:

| Parameter            | Beispiel                |
|----------------------|-------------------------|
| `config.broker`      | `mqtt.example.org`      |
| `config.topic`       | `mein/topic`            |
| `config.serialPort`  | `/dev/ttyUSB0`          |

**Wichtig:** Der Name der Application muss komplett kleingeschrieben sein (`radprogateway`). ArgoCD verwendet ihn als Helm-Release-Namen, und Helm lehnt Großbuchstaben ab (`invalid release name`). Alternativ unter Helm das Feld *Release Name* auf `radprogateway` setzen.

Eine Änderung von Broker, Topic oder Schnittstelle startet den Pod automatisch neu.

### Image-Updates

Das Image wird mit `imagePullPolicy: Always` und dem Tag `latest` geladen. Ein neuer Build wird erst beim nächsten Pod-Start übernommen, z. B. per:

```bash
kubectl -n radprogateway rollout restart deployment/radprogateway
```

### Fehlersuche

```bash
kubectl -n radprogateway get pods
kubectl -n radprogateway describe pod -l app=radprogateway   # Pending? -> Node-Label prüfen
kubectl -n radprogateway logs deploy/radprogateway           # fehlende Variablen, Seriell-/MQTT-Fehler
```
