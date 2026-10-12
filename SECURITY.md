# Revisão de segurança

Revisão realizada em 02/10/2026 sobre o código local da aplicação e os pacotes instalados no ambiente virtual. O escopo inclui importação Excel, persistência, rotas HTTP, templates e geração de relatórios. Não inclui teste de intrusão, infraestrutura publicada ou auditoria do executável Chrome/Chromium e da biblioteca JavaScript Chart.js.

## Achados e tratamento

| Prioridade | Achado | Situação |
| --- | --- | --- |
| Alta | `/imports`, `/imports/confirm` e `/api/imports` não exigem autenticação. Qualquer pessoa com acesso à aplicação pode importar dados e autorizar sua substituição. | Pendente: restringir as rotas a operadores autorizados antes da publicação, na aplicação ou em um proxy com autenticação. |
| Alta | O limite de tamanho do upload não impedia arquivos Excel com conteúdo descompactado excessivo ou XML malicioso. | Mitigado: limite de 50 MB descompactados, 256 entradas ZIP, 1000 linhas e três colunas, com `defusedxml` como dependência obrigatória. |
| Média | O limite de 10 MB é verificado depois que o framework processa o multipart. Uploads maiores podem consumir armazenamento temporário antes da rejeição. | Pendente: impor limite do corpo HTTP no proxy e considerar limitação de streaming antes do parser multipart. |
| Média | Não há limitação de requisições ou quota global para arquivos em revisão. As revisões expiram em 30 minutos, mas são removidas apenas na próxima validação. | Pendente: limitar importações e exportações por operador/IP e estabelecer limpeza periódica. O semáforo de exportação limita duas gerações por processo, não o total entre workers. |
| Média | Páginas de revisão podiam ser armazenadas em cache e não havia cabeçalhos contra enquadramento da interface. | Corrigido: `Cache-Control: no-store` nas rotas de importação, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e `Referrer-Policy: same-origin`. |
| Baixa | Posições numéricas acima do limite de inteiro do SQLite podiam gerar erro na persistência. | Corrigido: rejeição durante a validação da planilha. |

A validação limita tanto as dimensões declaradas quanto as linhas efetivamente lidas. Arquivos criptografados são rejeitados. Esses limites reduzem o risco de exaustão de recursos, mas não substituem controles de acesso e limites no servidor.

A proteção XML segue a [recomendação oficial do openpyxl](https://openpyxl.readthedocs.io/en/stable/index.html). Os [limites do parser multipart do Starlette](https://www.starlette.io/requests/) não equivalem a um limite global de upload de arquivos.

## Controles existentes verificados

- Consultas utilizam SQLAlchemy com parâmetros, sem construção de SQL a partir do conteúdo enviado pelo usuário nas rotas revisadas.
- Templates HTML utilizam escape automático e os dados dos gráficos são serializados com `tojson`. Os SVGs gerados escapam nomes e rótulos; os trechos marcados como HTML confiável vêm de recursos locais ou da geração controlada de gráficos.
- Importação e substituição são transacionais; falhas causam rollback.
- Tokens de revisão são gerados com `secrets.token_urlsafe`, expiram e são consumidos uma única vez. Eles identificam a revisão, mas não autenticam o operador.
- Nomes enviados não são utilizados como caminhos para gravar arquivos de upload.
- A exportação bloqueia requisições HTTP/HTTPS no navegador e usa diretórios temporários. Recursos locais continuam disponíveis para carregar as fontes do relatório.
- O banco e o ambiente virtual estão excluídos do versionamento pelo `.gitignore`.

## Auditoria de dependências

A execução de `pip-audit` consultou a base pública do PyPI e verificou **56 pacotes instalados**, sem pacotes ignorados e sem vulnerabilidades conhecidas encontradas. Esse resultado inclui dependências transitivas e as ferramentas de auditoria instaladas no ambiente; não garante ausência de vulnerabilidades nem cobre todas as versões permitidas por `requirements.txt`.

Para repetir a auditoria no ambiente utilizado em produção:

```bash
python -m pip install pip-audit
python -m pip_audit
```

As faixas de dependências não são um lockfile. Registre as versões aprovadas no processo de implantação e repita a auditoria após atualizações.

## Validação e pendências de publicação

Os testes de regressão de segurança estão em `tests/test_security.py`: expansão de ZIP, quantidade de entradas, entidades XML, dimensões adulteradas, overflow numérico e cabeçalhos HTTP. Execute a suíte com `python -m pytest -q`; os testes de exportação precisam iniciar o navegador.

Resultado nesta revisão: **38 testes passaram**, incluindo seis testes de segurança e seis de exportação. Houve um aviso de depreciação da integração Starlette/httpx, sem falhas. Os testes HTTP e de navegador foram executados fora do sandbox, que bloqueou a execução no ambiente restrito.

Antes da publicação, implemente o controle de acesso indicado acima, HTTPS no ponto de entrada, limites de corpo e de requisições e permissões de acesso ao banco. Caso a autenticação utilize cookies, inclua proteção CSRF nas rotas de alteração. Esta revisão não implementou um sistema de usuários nem avaliou configurações de um ambiente de produção.
