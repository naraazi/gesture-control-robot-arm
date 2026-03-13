# Gesture Control Robot Arm

Sistema de controle de um braço robótico por gestos de mão usando visão computacional em tempo real. O projeto combina um processo em Python, responsável por detectar landmarks da mão via câmera e traduzi-los em ângulos de servo, com um firmware Arduino que recebe esses comandos por serial e aciona quatro servomotores.

## Visão Geral

O objetivo do projeto é permitir que uma única mão humana controle, em tempo real, os quatro graus de atuação expostos pelo braço:

- rotação no eixo `x`
- movimento no eixo `y`
- movimento no eixo `z`
- abertura/fechamento da garra

O fluxo operacional é simples:

1. A câmera captura a mão do operador.
2. O MediaPipe Hands extrai os landmarks da mão.
3. O script Python converte esses landmarks em quatro ângulos.
4. Os ângulos são enviados como 4 bytes pela serial.
5. O Arduino atualiza os servos.
6. Se a comunicação parar por mais de 1 segundo, o firmware retorna o braço à posição padrão.

## Arquitetura

### 1. Camada de Visão e Controle

Arquivo principal: [main.py](/home/lorenzo/desenvolvimento/gesture-control-robot-arm/main.py)

Responsabilidades:

- capturar vídeo da câmera (`/dev/video2`)
- detectar uma mão por frame com `MediaPipe Hands`
- desenhar landmarks para depuração visual
- mapear gestos em ângulos de servo
- enviar ângulos pela porta serial (`/dev/ttyUSB0`) em `9600 baud`

Mapeamento atual implementado:

- `servo[0]` (`x`): usa a relação entre punho e base do dedo indicador para inferir a orientação da palma
- `servo[1]` (`y`): usa a coordenada vertical do punho
- `servo[2]` (`z`): usa o tamanho aparente da palma como aproximação de profundidade
- `servo[3]` (garra): fecha quando a mão é interpretada como punho fechado

### 2. Camada Embarcada

Arquivo principal: [main.ino](/home/lorenzo/desenvolvimento/gesture-control-robot-arm/main.ino)

Responsabilidades:

- inicializar 4 servos
- associar servos aos pinos `5`, `6`, `7` e `8`
- receber 4 bytes pela serial
- atualizar cada servo somente quando houver mudança de ângulo
- aplicar uma política de fail-safe por timeout

Posição padrão configurada no firmware:

- `x = 130`
- `y = 90`
- `z = 129`
- `claw = 110`

## Estrutura do Repositório

```text
.
├── main.py   # visão computacional, mapeamento de gestos e envio serial
└── main.ino  # firmware Arduino para acionamento dos servos
```

## Requisitos

### Hardware

- 1 placa Arduino compatível com a biblioteca `Servo`
- 4 servomotores
- 1 câmera acessível no host Linux
- braço robótico mecânico compatível com 4 canais de servo
- fonte de alimentação adequada para os servos
- conexão USB entre o computador e o Arduino

### Software

- Python 3
- Arduino IDE ou ferramenta equivalente para upload do sketch
- OpenCV para Python
- MediaPipe
- PySerial

Dependências Python esperadas pelo código:

```bash
pip install opencv-python mediapipe pyserial
```

## Como Executar

### 1. Carregar o firmware no Arduino

Compile e grave [main.ino](/home/lorenzo/desenvolvimento/gesture-control-robot-arm/main.ino) na placa.

Conexões de servo esperadas:

- pino `5`: servo do eixo `x`
- pino `6`: servo do eixo `y`
- pino `7`: servo do eixo `z`
- pino `8`: servo da garra

### 2. Validar dispositivos no host

O código assume:

- câmera em `/dev/video2`
- Arduino em `/dev/ttyUSB0`

Se o seu ambiente usar outros dispositivos, ajuste estes valores em [main.py](/home/lorenzo/desenvolvimento/gesture-control-robot-arm/main.py):

- `cam_source`
- `serial.Serial('/dev/ttyUSB0', 9600)`

### 3. Executar o controlador

```bash
python3 main.py
```

Ao iniciar:

- uma janela com o retorno da câmera será exibida
- os landmarks da mão serão desenhados na imagem
- os ângulos atuais aparecerão sobre o frame
- `ESC` encerra a execução

## Modos e Parâmetros Relevantes

O script expõe algumas flags e limites diretamente no código:

- `debug = False`: quando `True`, desabilita envio serial
- `write_video = False`: quando `True`, grava `output.avi`
- `fist_threshold = 7`: sensibilidade para detectar mão fechada
- intervalos `x_*`, `y_*`, `z_*`: calibração dos servos
- intervalos `palm_*` e `wrist_*`: calibração do mapeamento espacial

Esses valores são parte essencial da calibração do sistema e provavelmente precisam ser ajustados conforme:

- geometria do braço
- câmera utilizada
- distância entre usuário e câmera
- campo de visão
- torque e curso real dos servos

## Lógica de Controle

### Detecção de punho fechado

O algoritmo calcula a soma das distâncias entre o punho e pontas/intermediários dos dedos e normaliza esse valor pelo tamanho da palma. Quando a razão fica abaixo do limiar, a garra é fechada.

### Conversão de landmarks para servo

O método `landmark_to_servo_angle()` transforma dados da mão em ângulos com três operações principais:

- `clamp`: limita valores ao intervalo de segurança esperado
- `map_range`: remapeia uma medida de entrada para a faixa angular do servo
- cast para `int`: garante envio como bytes discretos

Os ângulos são transmitidos em tempo real como um vetor de quatro posições:

```text
[x, y, z, claw]
```

## Segurança Operacional

O firmware implementa uma proteção simples e útil: se nenhum comando for recebido por mais de 1000 ms, todos os servos retornam à posição padrão.

Isso reduz risco em casos como:

- travamento do processo Python
- desconexão do cabo USB
- perda de detecção da mão
- interrupção momentânea da câmera

Ainda assim, para uso físico real, recomenda-se:

- alimentar servos com fonte externa apropriada
- compartilhar GND entre fonte e Arduino
- validar limites mecânicos antes de operação contínua
- testar primeiro com o braço desacoplado de carga

## Limitações Observadas no Código Atual

O repositório já indica um ponto sensível no controle de profundidade: os parâmetros `palm_size_min` e `palm_size_max` estão marcados no código como um “major (live) problem”. Na prática, isso significa que o eixo `z` depende de uma heurística frágil, baseada no tamanho aparente da mão na imagem, e tende a variar com iluminação, perspectiva e distância da câmera.

Outras limitações importantes:

- os caminhos de dispositivo são fixos e específicos de Linux
- não há arquivo de configuração externo
- não há tratamento explícito para perda de serial na inicialização
- o sistema foi desenhado para operar com exatamente uma mão visível
- não há suíte de testes automatizados
- o protocolo serial é mínimo e não inclui checksum, framing ou telemetria

## Troubleshooting

### A câmera não abre

Verifique se `/dev/video2` existe e se corresponde ao dispositivo correto. Se necessário, troque `cam_source`.

### O Arduino não responde

Confirme:

- porta serial correta
- baud rate em `9600`
- permissões do usuário para acessar `/dev/ttyUSB0`
- firmware gravado corretamente

### O braço se move de forma errática

Revise a calibração de:

- `x_min`, `x_mid`, `x_max`
- `y_min`, `y_mid`, `y_max`
- `z_min`, `z_mid`, `z_max`
- `palm_angle_*`
- `wrist_y_*`
- `palm_size_*`

### A garra fecha em momentos errados

Ajuste `fist_threshold` e valide a câmera com fundo limpo e iluminação estável.

## Público-Alvo

Este projeto é adequado para:

- prototipagem de interfaces naturais homem-máquina
- demonstrações acadêmicas de visão computacional aplicada à robótica
- experimentação com MediaPipe e controle embarcado
- estudos de teleoperação de baixo custo
