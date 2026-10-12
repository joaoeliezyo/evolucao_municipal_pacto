# Dashboard Pacto pelo Piauí

![Python](https://img.shields.io/badge/Python-3776AB?style=flat)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat)
![Uvicorn](https://img.shields.io/badge/Uvicorn-4051B5?style=flat)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat)
![openpyxl](https://img.shields.io/badge/openpyxl-217346?style=flat)
![defusedxml](https://img.shields.io/badge/defusedxml-3776AB?style=flat)
![Jinja2](https://img.shields.io/badge/Jinja2-B41717?style=flat)
![python-multipart](https://img.shields.io/badge/python--multipart-3776AB?style=flat)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat)
![httpx](https://img.shields.io/badge/httpx-009688?style=flat)
![pypdf](https://img.shields.io/badge/pypdf-3776AB?style=flat)

Aplicação web para acompanhar a evolução mensal das posições de 12 municípios no Pacto pelo Piauí. Centraliza a importação de planilhas Excel, o histórico municipal e a análise dos resultados em um dashboard com filtros, indicadores e relatórios exportáveis.

Desenvolvida em Python com FastAPI, SQLAlchemy e SQLite, com interface em português e identidade visual baseada no Ranking Municipal da JUCEPI.

## Funcionalidades

- **Importação com revisão:** validação de arquivos Excel antes da gravação e confirmação explícita para substituir períodos existentes.
- **Dashboard interativo:** filtros por ano, mês e município, indicadores de desempenho e ranking de evolução mensal.
- **Histórico municipal:** gráficos e tabelas com as posições armazenadas, inclusive entre anos diferentes.
- **Ranking de evolução:** classificação com critérios de desempate e medalhas para os três primeiros municípios com comparação válida.
- **Exportação de relatórios:** PDF com texto pesquisável e gráficos vetoriais ou ZIP com imagens PNG.
- **Interface responsiva:** adaptação a dispositivos móveis, com fontes, imagens e Chart.js servidos localmente.
- **API documentada:** validação e importação de planilhas via HTTP, com documentação interativa em `/docs`.

## Tecnologias

| Camada | Tecnologias |
| --- | --- |
| Aplicação e servidor | Python 3.12+, FastAPI e Uvicorn |
| Persistência | SQLAlchemy e SQLite |
| Leitura de planilhas | openpyxl e defusedxml |
| Interface | Jinja2, CSS, JavaScript e Chart.js |
| Exportação | Playwright e Chrome/Chromium |
| Testes | pytest, httpx e pypdf |

## Instalação e execução

### Pré-requisitos

- Python 3.12 ou superior, com `pip` e suporte a `venv`.
- Chrome/Chromium disponível para gerar relatórios e executar os testes de exportação.

Execute os comandos a partir da raiz do repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

No Windows, ative o ambiente virtual com `.venv\Scripts\Activate.ps1` no PowerShell.

| Acesso local | Endereço |
| --- | --- |
| Dashboard | http://127.0.0.1:8000/dashboard |
| Importação de planilhas | http://127.0.0.1:8000/imports |
| Documentação da API | http://127.0.0.1:8000/docs |

O banco `data/app.db` e as tabelas são criados automaticamente na inicialização. Em uma instalação nova, importe uma planilha para preencher o dashboard. A opção `--reload` é destinada ao desenvolvimento local.

### Navegador para exportação

A aplicação detecta executáveis `google-chrome`, `chromium` ou `chromium-browser` disponíveis no sistema. Se necessário, instale o Chromium do Playwright:

```bash
python -m playwright install chromium
```

Também é possível indicar um executável existente com `EXPORT_BROWSER_PATH`. O ambiente de execução precisa permitir que o servidor inicie o navegador.

### Configuração

| Variável de ambiente | Finalidade | Padrão |
| --- | --- | --- |
| `DATABASE_URL` | Caminho de conexão com outro banco SQLite | `data/app.db` na raiz do projeto |
| `EXPORT_BROWSER_PATH` | Caminho do executável Chrome/Chromium | Detecção automática; na ausência, Chromium do Playwright |

Exemplo com um banco alternativo:

```bash
export DATABASE_URL='sqlite:////tmp/pacto.db'
python -m uvicorn app.main:app --reload
```

## Importação de dados

1. Acesse `/imports` e selecione um arquivo `.xlsx` de até **10 MB**, com até **1000 linhas** (incluindo o cabeçalho).
2. Informe o ano de referência, entre **1900 e 2100**.
3. Selecione um mês ou **Todos os meses do arquivo**.
4. Clique em **Validar e revisar** e confira os registros, meses e períodos existentes.
5. Clique em **Confirmar importação**. Caso haja dados nos períodos apresentados, confirme a substituição.

Após a confirmação, o dashboard abre no ano informado e no último mês do arquivo. A revisão permanece disponível por **30 minutos** e só pode ser confirmada uma vez. A gravação ocorre em uma única transação; em caso de falha, a revisão permanece disponível para nova tentativa dentro do prazo.

A substituição troca todos os registros dos períodos presentes no arquivo e preserva os demais meses. Assim, um arquivo com um mês incompleto substitui também os dados anteriores daquele mês.

### Formato da planilha

A aba deve se chamar **`Planilha1`**, com estas três colunas, nesta ordem:

| MUNICIPIO | POSIÇÃO | MÊS |
| --- | ---: | --- |
| BETANIA | 217 | JANEIRO |
| BURITI DOS MONTES | 100 | JANEIRO |
| CAMPO LARGO | 180 | JANEIRO |

- `MUNICIPIO`: um dos 12 municípios cadastrados em `app/services/import_service.py`, conforme o PRD.
- `POSIÇÃO`: número inteiro positivo.
- `MÊS`: nome do mês em português, de `JANEIRO` a `DEZEMBRO`.

O conteúdo descompactado é limitado a **50 MB** e o arquivo pode conter até **256 entradas ZIP**. Planilhas criptografadas são rejeitadas.

O ano é informado na importação e não faz parte da planilha. Cabeçalhos, municípios e meses são comparados ignorando espaços extras e diferenças entre maiúsculas e minúsculas; a grafia e os acentos do contrato devem ser respeitados. O nome original do município é preservado no cadastro.

Linhas totalmente vazias são ignoradas. Municípios desconhecidos, posições inválidas e registros duplicados para o mesmo município no mesmo mês impedem a importação. Meses incompletos são aceitos, com a quantidade de registros exibida na revisão. A seleção de um mês específico exige que **todas as linhas** pertençam àquele mês.

O arquivo de referência `COLOCAÇÃO PACTO.xlsx` contém **108 registros**, distribuídos entre janeiro e setembro, com 12 municípios por mês. Consulte o [contrato de entrada](04_CONTRATO_EXCEL.md) para mais detalhes.

## Dashboard e regras de cálculo

O dashboard seleciona inicialmente o período mais recente armazenado. Os filtros são aplicados automaticamente; **Limpar filtros** retorna ao período mais recente com todos os municípios, e **Último disponível** seleciona o último mês do ano informado. Um período sem dados apresenta um estado vazio.

### Evolução mensal

```text
evolução = posição anterior − posição atual
```

Por exemplo, passar da posição 100 para a 80 representa uma evolução de **+20 posições**. Valores positivos indicam melhora, negativos indicam queda e zero indica estabilidade.

A comparação exige um registro do mesmo município no mês imediatamente anterior, inclusive na passagem de dezembro para janeiro. O primeiro registro e os meses após uma lacuna exibem **Sem comparação**. Posição anterior e evolução são calculadas pelo sistema.

### Classificação e indicadores

A tabela ordena os municípios pela maior evolução, com desempate pela melhor posição atual e, depois, pelo nome. Registros sem comparação ficam ao final. As medalhas consideram todos os municípios do período e mantêm essa classificação quando um município é filtrado.

Os indicadores acompanham os municípios exibidos pelos filtros:

- Melhora, queda, estabilidade e evolução mediana consideram apenas comparações mensais válidas; os registros sem comparação são informados separadamente.
- A melhor posição atual corresponde ao menor número, com desempate pelo nome.
- A evolução acumulada no ano corresponde à primeira posição disponível no ano menos a posição do período selecionado. Exige ao menos dois registros no ano e é resumida pela mediana do grupo exibido.

Os gráficos do dashboard mostram o histórico de janeiro até o mês selecionado. Meses ausentes não são conectados, e a posição 1 aparece no topo do eixo. Ao clicar no nome de um município, é possível consultar todo o seu histórico em `/municipios/{municipio_id}`.

## Exportação de relatórios

Use o menu de exportação no canto inferior direito do dashboard para gerar um relatório com os filtros atuais. Cada relatório contém **três páginas no formato 16:10**:

1. Indicadores de desempenho.
2. Tabela de posições e histórico no ano.
3. Gráficos individuais na ordem do ranking de evolução.

| Formato | Arquivo gerado |
| --- | --- |
| PNG | ZIP com três imagens de 1600 × 1000 pixels |
| PDF | Documento de três páginas, com textos selecionáveis e gráficos SVG vetoriais |

Os relatórios incluem período, filtro, data e hora de Fortaleza e numeração das páginas. A geração usa recursos locais, arquivos temporários e admite até duas exportações simultâneas. Períodos sem registros não podem ser exportados.

## API

### Importar planilha

`POST /api/imports` recebe `multipart/form-data`:

| Campo | Tipo | Comportamento |
| --- | --- | --- |
| `arquivo` | Arquivo `.xlsx` | Obrigatório |
| `ano` | Inteiro | Obrigatório; entre 1900 e 2100 |
| `mes` | Inteiro | `0` para todos os meses (padrão) ou `1` a `12` |
| `confirmar` | Booleano | `false` apenas valida (padrão); `true` grava |
| `substituir` | Booleano | `true` autoriza substituir períodos existentes; padrão `false` |

Exemplo de validação, sem gravar dados:

```bash
curl http://127.0.0.1:8000/api/imports \
  -F 'arquivo=@COLOCAÇÃO PACTO.xlsx' \
  -F ano=2026 \
  -F mes=0
```

Informe o ano real dos dados. Para gravar, acrescente `-F confirmar=true`; para autorizar a substituição de períodos existentes, acrescente também `-F substituir=true`.

A resposta JSON contém `status`, `arquivo`, `ano`, `quantidade`, `meses` e `competencias_existentes`. A API retorna **400** para erros de validação, **409** para conflitos, **413** para arquivos acima do limite e **422** para parâmetros obrigatórios ausentes ou tipos inválidos.

### Exportar relatório

`GET /api/exports/{png|pdf}` recebe os parâmetros opcionais `ano`, `mes` e `municipio_id`, com os mesmos filtros do dashboard. Consulte `/docs` para explorar os endpoints.

## Estrutura do projeto

```text
app/
├── main.py                  # Inicialização e rotas HTTP
├── database.py              # Conexão e sessões SQLite
├── models.py                # Modelos e restrições de integridade
├── schemas.py               # Esquemas de resposta da API
├── services/
│   ├── import_service.py    # Leitura, validação e persistência
│   ├── ranking_service.py   # Evolução, indicadores e histórico
│   └── export_service.py    # Geração de relatórios PNG e PDF
├── templates/               # Páginas e relatórios Jinja2
└── static/                  # CSS, JavaScript, fontes e identidade visual
assets/                      # Medalhas e ícones SVG
data/                        # Banco SQLite local, não versionado
tests/                       # Testes automatizados
requirements.txt             # Dependências Python
```

## Testes

Com o ambiente virtual ativo e as dependências instaladas:

```bash
python -m pytest -q
```

A suíte utiliza bancos temporários e cobre validação de planilhas, confirmação, substituição, rollback, evolução mensal, filtros, lacunas no histórico, passagem de ano, navegação HTTP e exportações. Os testes de exportação precisam iniciar Chrome/Chromium.

## Documentação do projeto

| Documento | Conteúdo |
| --- | --- |
| [Requisitos do produto](01_PRD.md) | Objetivos, municípios e critérios de aceite |
| [Arquitetura](02_ARQUITETURA.md) | Organização técnica e fluxos implementados |
| [Modelo de dados](03_MODELO_DADOS.sql) | Esquema SQL de referência |
| [Contrato Excel](04_CONTRATO_EXCEL.md) | Estrutura e validações da planilha |
| [Checklist de testes](06_CHECKLIST_TESTES.md) | Verificações e pendências de homologação |
| [Especificação visual](07_UI_SPEC.md) | Decisões de interface e identidade visual |
| [Estado do projeto](08_ESTADO_PROJETO.md) | Entrega atual e próximos passos |

A publicação e a homologação no ambiente de destino permanecem pendentes. A aplicação cria tabelas ausentes na inicialização, mas não possui um sistema de migrações para atualizar tabelas existentes. O SQL de referência não deve ser usado como migração do banco de trabalho.

## Segurança

A revisão de segurança, os problemas corrigidos e as pendências estão em [SECURITY.md](SECURITY.md). As rotas de importação ainda não possuem autenticação: quem consegue acessar a aplicação pode importar e substituir dados. Antes de publicá-la, restrinja essas rotas a operadores autorizados.
