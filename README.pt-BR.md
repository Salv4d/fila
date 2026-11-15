# fila

[![test](https://github.com/Salv4d/fila/actions/workflows/test.yml/badge.svg)](https://github.com/Salv4d/fila/actions/workflows/test.yml)

**Um Kafka de bolso pro Claude Code.**

Migrations no estilo Rails pro seu trabalho pendente: script roda uma vez e o id vai pra um log que
só cresce, tarefa espera o agente, e a fila aparece toda vez que uma sessão começa.

🇺🇸 [Read in English](README.md)

![fila status e o que o Claude Code vê ao abrir a sessão](docs/screenshot.png)

Você começa um render longo, uma transcrição, um processamento em lote. A sessão acaba, o notebook
dorme, você esquece. Na próxima vez que abre o Claude Code, ninguém sabe o que ficou pela metade.

A `fila` resolve isso com uma ideia que todo dev Rails já conhece: **a migration é o que precisa
ser feito; gravar o id dela é a prova de que foi feito.**

- Cada trabalho pendente é um arquivo em `.fila/migrations/`, com nome `<timestamp>_<nome>`.
- `fila run` executa os pendentes **na ordem do id** e anota cada id em `.fila/done`, do mesmo
  jeito que o Rails grava na `schema_migrations`.
- Se um falha, a fila para ali. O que vem depois não roda, e o id que falhou não é anotado.
- Um **hook de SessionStart** conta pro Claude Code o que ainda está pendente assim que a sessão
  abre, e o agente continua de onde você parou.

Por que "Kafka de bolso": o consumidor do Kafka não pergunta "já processei isso?", ele lê o offset
que gravou. A `fila` faz o mesmo com o `.fila/done`, um log que só cresce com os ids executados, que
é exatamente o que a `schema_migrations` do Rails é. Sem broker, sem partição, sem cluster: um
arquivo e um log em texto, do tamanho de uma pessoa e um agente.

Um arquivo só, só biblioteca padrão do Python 3, sem serviço rodando, sem banco. A fila é texto
puro: dá pra commitar, comparar e revisar.

## Dois tipos de migration

| Tipo | Arquivo | O que acontece |
|---|---|---|
| **script** | `.sh`, `.py` ou qualquer executável | `fila run` executa a partir da raiz do projeto. Saiu com 0 = feito. |
| **tarefa** | `.md` | Instrução pra uma pessoa ou pra um agente de IA (revisar, decidir, escrever). Fecha com `fila done <id>`. |

As tarefas são o que deixa isso útil com agente: trabalho que precisa de julgamento também entra
na fila, e o Claude Code vê no começo da próxima sessão.

## Instalar

### Como plugin do Claude Code (recomendado)

Dentro do Claude Code (2.1.275 ou mais novo):

```
/plugin install fila --marketplace Salv4d/fila
```

Em versão mais antiga, dois passos: `/plugin marketplace add Salv4d/fila` e depois `/plugin install fila@fila`.

Isso traz o hook de SessionStart, o comando `fila` no PATH do agente e três comandos de barra:

| Comando | O que faz |
|---|---|
| `/fila:status` | Mostra a fila e sugere o próximo passo |
| `/fila:new <o quê>` | Põe trabalho novo na fila: o Claude decide se é script ou tarefa e escreve o arquivo |
| `/fila:run` | Roda os scripts pendentes (em segundo plano quando são longos) e conta o resultado |

Funciona no terminal, no app desktop e na extensão do VS Code, porque eles leem as mesmas
configurações no computador. Não funciona no chat do claude.ai nem em sessão na nuvem: lá não
existe pasta local.

### Como CLI avulsa

```bash
curl -fsSL https://raw.githubusercontent.com/Salv4d/fila/main/fila -o ~/.local/bin/fila
chmod +x ~/.local/bin/fila
fila install-hook --global   # dentro de um projeto: hook no ~/.claude/settings.json + projeto registrado
```

Use um dos dois jeitos, não os dois, senão o hook roda duas vezes.

### Windows

Funciona com Python 3.8+ (`python`, `python3` ou o lançador `py`) e o Git for Windows, que é
também o que o Claude Code usa pra rodar hooks. Migration `.py` roda em qualquer lugar; `.sh`
precisa do bash (Git Bash). O CI roda os testes em Linux, macOS e Windows.

## Começo rápido

```bash
cd meu-projeto
fila init                                  # cria .fila/
fila install-hook                          # põe o hook de SessionStart no .claude/settings.json
fila new "render final"                    # .fila/migrations/20261114224000_render_final.sh
fila new "revisar legenda" --md            # tarefa pra uma pessoa ou pro agente
$EDITOR .fila/migrations/*render_final.sh
fila status
fila run                                   # roda os scripts pendentes, em ordem
fila done 20261114224500                   # fecha uma tarefa
```

Migration de script é um script comum. A primeira linha de comentário é a descrição:

```bash
#!/usr/bin/env bash
# Renderiza o corte final com b-roll e música
set -euo pipefail
python3 scripts/render.py bruto.mkv --out final.mp4
```

## Comandos

| Comando | O que faz |
|---|---|
| `fila init` | Cria `.fila/` (`migrations/`, `done`, `logs/`) na pasta atual. |
| `fila new <nome> [--md]` | Migration nova com id de data e hora. `--md` cria uma tarefa. |
| `fila status [--json]` | Pendentes e feitas, da mais antiga pra mais nova. Só `fila` faz o mesmo. |
| `fila run [ID ...] [--dry-run]` | Roda os scripts pendentes em ordem. Para na primeira falha. |
| `fila done ID ...` | Anota ids sem rodar (tarefas, ou coisa feita na mão). |
| `fila undo ID ...` | Devolve migrations pra fila (o "rollback"). |
| `fila log ID` | Saída da última execução (`.fila/logs/<id>.log`). |
| `fila hook` | O hook de SessionStart. Não imprime nada quando não há pendência. |
| `fila install-hook [--global]` | Põe o hook no `.claude/settings.json`. `--global`: no `~/.claude/settings.json`, e registra este projeto. |
| `fila projects [--remove PASTA]` | Lista (ou tira) os projetos que o hook global acompanha. |

Os ids aceitam um prefixo único ou o nome da migration.

## Como o hook funciona

`fila install-hook` acrescenta isto ao `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "\"/home/voce/.local/bin/fila\" hook", "timeout": 10 }] }
    ]
  }
}
```

Quando tem pendência, `fila hook` mostra um aviso curto pra você (`fila: 3 pending`) e coloca a
lista no contexto do Claude, com a instrução: rodar os scripts, fazer as tarefas e fechar com
`fila done`. Sem pendência, não imprime nada e não custa nada.

O hook só **lê** a fila. Nunca roda migration sozinho. Rodar é sempre um `fila run` explícito,
seu ou do agente.

## Um hook, vários projetos

Se você abre o Claude Code na sua pasta pessoal (ou em qualquer lugar fora do projeto), o hook do
projeto nunca dispara. Rode isto uma vez dentro de cada projeto:

```bash
fila install-hook --global
```

Ele põe o hook no `~/.claude/settings.json` e registra o projeto em `~/.config/fila/projects`. Daí
em diante, toda sessão, de onde quer que comece, recebe o trabalho pendente de todos os projetos
registrados. `fila projects` mostra a lista.

## O que vai pro git

Commite `.fila/migrations/` e `.fila/done`: é o histórico do que foi feito e quando. O
`fila init` cria um `.fila/.gitignore` que deixa `logs/` e a trava de execução de fora.

## Detalhes

- **Ordem** é a do id (timestamp), nunca a data de modificação do arquivo.
- **Pasta de trabalho** de todo script é a raiz do projeto (a pasta que tem a `.fila/`), mesmo
  chamando `fila` de uma subpasta. Os scripts recebem `FILA_ID` e `FILA_ROOT` no ambiente.
- **Concorrência**: um arquivo de trava impede dois `fila run` ao mesmo tempo.
- **Formato do `.fila/done`**: uma linha por id, `id<TAB>ran|marked<TAB>data-iso<TAB>duração`.

## Parecidos, e onde a fila é diferente

| Projeto | O que é | Diferença |
|---|---|---|
| [Beads](https://github.com/steveyegge/beads) | Rastreador de issues no git que dá memória ao agente entre sessões | Rastreia issues (status, prioridade, dependência); não executa nada. A `fila` roda script uma vez e anota |
| [Backlog.md](https://github.com/MrLesk/Backlog.md) | Quadro de tarefas em Markdown pra gente e pra agente | É um quadro, não uma fila ordenada que roda cada coisa uma vez |
| [Taskmaster AI](https://github.com/eyaltoledano/claude-task-master) | Quebra um documento de requisitos em tarefas pro agente | Planejamento; a `fila` é o trabalho já decidido que ainda precisa acontecer |
| [scriptup](https://github.com/mg98/scriptup), [TerraRatchet](https://github.com/triptease/terra-ratchet) | Executores de script que rodam uma vez, no estilo migration | A mesma ideia pros scripts, mas sem agente: sem tarefa, sem hook de sessão |

Se você precisa de um rastreador de issues completo pro agente, use o Beads. Se precisa de "isso
tem que acontecer, uma vez, nessa ordem, e o agente não pode esquecer", é a `fila`.

## Testes

```bash
python3 -m unittest discover -s tests
```

## Licença

MIT
