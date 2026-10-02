# Dashboard Pacto pelo Piauí

Este pacote foi atualizado a partir da planilha real de entrada `COLOCAÇÃO PACTO.xlsx`.

## Formato real identificado

A planilha possui uma única aba (`Planilha1`) com 109 linhas e 3 colunas:

- `MUNICIPIO`
- `POSIÇÃO`
- `MÊS`

Há 12 municípios por mês, de JANEIRO a SETEMBRO, totalizando 108 registros de dados.

## Regra de importação

O sistema deve receber:
1. arquivo Excel;
2. ano de referência informado pelo usuário.

O mês pode ser obtido da coluna `MÊS`. Para segurança, a interface pode permitir informar o mês e validar que ele coincide com os valores encontrados no arquivo.

A posição anterior e a evolução NÃO devem ser importadas: devem ser calculadas pelo sistema.

## Stack sugerida

- Python 3.12+
- FastAPI
- SQLAlchemy
- SQLite
- pandas + openpyxl
- Jinja2
- Chart.js
- pytest

Consulte o PRD, a arquitetura, o contrato de entrada e a especificação visual neste repositório.

## Aplicação de importação

A aplicação implementada usa FastAPI, Jinja2, openpyxl e SQLAlchemy com SQLite.
O openpyxl lê diretamente o contrato simples de três colunas, sem necessidade de pandas.

### Executar

Requer Python 3.12+ com suporte a `venv` e pip.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Acesse http://127.0.0.1:8000/ para o dashboard ou http://127.0.0.1:8000/imports para importar. O banco `data/app.db` e suas tabelas
são criados automaticamente ao iniciar. Para outro banco SQLite, configure
`DATABASE_URL`, por exemplo `sqlite:////tmp/pacto.db`.

### Importar

1. Selecione um `.xlsx` de até 10 MB e informe o ano (1900 a 2100).
2. Selecione o mês correspondente ou “Todos os meses do arquivo”. O mês específico
   exige que todas as linhas pertençam àquela competência; não filtra silenciosamente.
3. Clique em “Validar e revisar” para ver os registros e meses encontrados.
4. Clique em “Confirmar importação”, sem selecionar o arquivo novamente. Caso existam competências,
   marque a confirmação explícita de substituição. Após a gravação, o navegador abre
   o dashboard no ano informado e no último mês contido no arquivo. Atualizar essa
   página não reenvia a importação.

Os municípios aceitos são os 12 definidos no PRD. Nomes são comparados ignorando
espaços extras e diferenças de caixa; o nome original é preservado no cadastro.
Meses e cabeçalhos devem seguir o contrato documentado. Linhas totalmente vazias são
ignoradas; posições inválidas e municípios duplicados no mês impedem a importação.
Arquivos com meses incompletos são aceitos; a quantidade é mostrada na revisão.

O arquivo validado é mantido temporariamente no banco por 30 minutos. A confirmação
usa esse mesmo arquivo e os parâmetros revisados, valida novamente e grava em uma
única transação. A revisão só pode ser confirmada uma vez; se a gravação falhar,
ela continua disponível para tentar novamente dentro do prazo. Revisões expiradas
são removidas na próxima validação de arquivo.
A substituição remove posições apenas das competências contidas no novo arquivo,
preservando os demais meses. O horário de importação é exibido em UTC.

### API de importação

`POST /api/imports` recebe `multipart/form-data` e retorna JSON:

| Campo | Descrição |
|---|---|
| `arquivo` | Planilha `.xlsx`, obrigatória |
| `ano` | Ano de referência, obrigatório |
| `mes` | 1 a 12; 0 (padrão) importa todos os meses |
| `confirmar` | `false` (padrão) valida sem gravar; `true` grava |
| `substituir` | `true` autoriza substituir as competências já existentes |

Exemplo de gravação:

```bash
curl http://127.0.0.1:8000/api/imports \
  -F 'arquivo=@COLOCAÇÃO PACTO.xlsx' \
  -F ano=2026 -F mes=0 -F confirmar=true
```

A resposta informa `status`, `arquivo`, `ano`, `quantidade`, `meses` e
`competencias_existentes`. Erros de validação retornam 400, conflitos 409,
arquivos acima do limite 413 e parâmetros ausentes ou de tipo inválido 422.
Consulte e experimente o endpoint em http://127.0.0.1:8000/docs.

### Arquivos da aplicação

- `app/main.py`: inicialização e rotas do dashboard, histórico e importação.
- `app/services/ranking_service.py`: consultas de posições, evolução e histórico.
- `app/database.py`: conexão, sessões e ativação de chaves estrangeiras SQLite.
- `app/models.py`: municípios, períodos e posições com restrições de integridade.
- `app/services/import_service.py`: leitura, validação e persistência transacional.
- `app/templates/` e `app/static/`: interface responsiva em português.
- `tests/`: validação de planilhas, persistência, substituição e rollback.

Para executar os testes:

```bash
python -m pytest -q
```

Os testes utilizam bancos temporários e conferem a planilha real, os 12 resultados
de evolução de setembro, primeiro mês, filtros, lacunas no histórico, virada do ano
e navegação HTTP.

### Dashboard e histórico

Após importar a planilha, abra `/` ou `/dashboard`. A seleção inicial usa o último
ano e mês armazenados. Os filtros são aplicados automaticamente ao escolher ano,
mês ou município. O botão “Limpar filtros” abre o período mais recente com todos
os municípios. “Último
disponível” escolhe o último mês do ano informado. Períodos sem dados mostram um
estado vazio, sem substituir a seleção por outro mês.

A tabela “Posições atuais” reúne a posição no ranking de evolução, o município,
as posições anterior e atual e a evolução. Ela ordena os municípios da maior para a
menor, com os registros sem comparação ao final. Em caso de empate, usa a melhor
posição atual e depois o nome. Os cards e seus números seguem essa mesma classificação pela evolução.
O ranking de evolução fica nessa mesma tabela. Os três primeiros recebem medalhas
de ouro, prata e bronze após o nome, usando os SVGs da pasta `assets/`. As
medalhas consideram todos os municípios do período e mantêm a classificação
ao filtrar um município. Sem comparação mensal, não há medalha. O dashboard apresenta
maior subida, maior queda, cards com histórico mensal e gráficos de linha.
Os cards individuais usam linha azul (`#1e40af`) com pontos e posições anotadas, meses no
eixo horizontal e resumo de posição anterior, atual e evolução. Históricos longos
permitem rolagem dentro do gráfico em telas pequenas. Os
indicadores consideram os municípios exibidos pelo filtro. Empates nos destaques
são resolvidos pela ordenação do ranking; todos os valores permanecem visíveis.
Clique no nome de um município para abrir `/municipios/{id}`, com gráfico e tabela
de todo o histórico armazenado, incluindo anos diferentes.

A evolução é `posição anterior - posição atual`. A comparação exige dados do mês
imediatamente anterior para aquele município, inclusive dezembro/janeiro. O
primeiro período ou um mês após uma lacuna mostra “Sem comparação”. Meses ausentes
não são conectados no gráfico. A posição 1 aparece no topo do eixo vertical.

Chart.js 4.4.8 é servido localmente em `app/static/vendor/`, com sua licença MIT.
Os gráficos são interativos, gerados com as posições reais do banco; ao passar o
mouse ou tocar no gráfico, o tooltip mostra mês e posição. O histórico no dashboard
vai de janeiro até o mês selecionado, ou até a última competência disponível quando
não há filtros. A mudança de filtro recalcula os gráficos. As tabelas e valores
mensais permanecem disponíveis se o JavaScript não carregar.
O layout adapta filtros e cards a telas pequenas; as tabelas permitem rolagem
horizontal. O dashboard foi conferido no Chrome headless em larguras de 1440 e
390 pixels, com os 13 gráficos carregados e sem transbordamento horizontal da página.
A publicação e a homologação no ambiente de destino permanecem pendentes.

### Indicadores adicionais

Os indicadores acompanham os filtros. Quantidade e percentual de municípios que
melhoraram, pioraram e ficaram estáveis usam apenas comparações mensais válidas;
a quantidade sem comparação é informada. A evolução mediana usa essa mesma base.
A melhor posição atual usa a menor posição, com desempate pelo nome.
A evolução acumulada no ano é calculada por município (primeira posição disponível
no ano menos posição selecionada) e resumida pela mediana do grupo exibido. Exige
ao menos dois registros no ano; a quantidade excluída é mostrada no card.

### Exportação em PNG e PDF

O ícone de exportação usa o SVG original de `assets/export.svg`, sem recoloração,
e fica no canto inferior direito do dashboard. O menu exibe apenas “PDF” e “PNG”,
com largura ajustada ao conteúdo. Os filtros permanecem visíveis durante a rolagem;
em telas pequenas os controles ficam compactos. Em celulares na horizontal com pouca altura,
os filtros voltam ao fluxo da página para liberar a área de leitura.

A exportação considera ano, mês e município exibidos e produz três páginas 16:10,
cada uma com cabeçalho e rodapé com período, filtro, data/hora de Fortaleza e número:

1. Indicadores (KPIs).
2. Tabela de posições e histórico no ano.
3. Todos os gráficos individuais, na ordem do ranking de evolução.

“PNG” baixa um ZIP com três imagens de 1600 × 1000 pixels. “PDF” baixa um
PDF de três páginas com textos selecionáveis e gráficos SVG vetoriais; títulos,
nomes dos municípios, valores e rótulos dos gráficos são pesquisáveis. O relatório
usa os dados até o mês selecionado e incorpora as medalhas, sem depender de rede.
Os dados são consultados ao clicar em exportar, usando os filtros atuais.

A geração usa Playwright com Chrome/Chromium. Neste ambiente o Chrome instalado é
detectado automaticamente. Em outra máquina, após instalar `requirements.txt`,
instale um navegador com `python -m playwright install chromium`, ou configure
`EXPORT_BROWSER_PATH` com o caminho de um Chrome/Chromium existente. O servidor
precisa poder iniciar esse navegador. A geração usa arquivos temporários e permite
até duas exportações simultâneas; a interface apresenta mensagens de progresso e erro.

A rota `GET /api/exports/{png|pdf}` aceita `ano`, `mes` e `municipio_id`, assim como
o dashboard. Períodos sem registros não podem ser exportados.

### Identidade visual

A interface segue a identidade do [Ranking Municipal da JUCEPI](https://rankingmunicipal.jucepi.pi.gov.br/):
cabeçalho azul institucional, fundo cinza claro, cards brancos com sombras discretas,
KPIs sem ícones, tabela com cabeçalho azul e rodapé institucional. O tema é
compartilhado pelo dashboard, importação, histórico individual e relatórios exportados.

O rodapé reproduz os textos, links e ícones da referência, incluindo órgão,
atendimento, redes sociais, sites e créditos. Fica na base da tela em páginas curtas
e após o conteúdo em páginas longas.

Os logotipos públicos do site estão em `app/static/brand/`. As fontes Inter e Space
Grotesk estão em `app/static/fonts/`, com suas licenças SIL Open Font License. Fontes,
logotipos, medalhas e biblioteca de gráficos são servidos localmente. O layout mantém
1600 px de largura máxima, seis KPIs e três gráficos individuais por linha em desktop,
com controles e colunas adaptados ao celular.

O estado de entrega e os próximos passos estão em [08_ESTADO_PROJETO.md](08_ESTADO_PROJETO.md).
