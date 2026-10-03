# T3 Code Windows Launcher

Lançador discreto para executar o servidor local do [T3 Code](https://github.com/pingdotgg/t3code) no Windows.

O launcher mantém a consola escondida, abre a interface no Google Chrome e usa um único ícone na barra de tarefas.

## Instalação

1. Instale o Python 3 e o Google Chrome.
2. Descarregue uma versão do T3 Code para Windows.
3. Extraia o conteúdo da distribuição para a pasta `runtime` deste projecto.
4. Confirme que existe `runtime\t3.exe`.
5. Execute `install.ps1` no PowerShell.

O instalador cria atalhos no Ambiente de Trabalho, menu Iniciar e arranque automático do Windows.

## Utilização

Clique no atalho **T3 Code**. O servidor inicia sem consola visível e a interface abre em `http://localhost:3773`.

O diagnóstico fica em `t3-launcher.log`. O launcher remove os tokens de emparelhamento antes de escrever o registo.

## Publicação segura

O repositório não contém o runtime do T3 Code, credenciais, tokens, registos locais ou caches Python.

Consulte [LEIA-ME.md](LEIA-ME.md) para conhecer o contexto, a arquitectura e a solução de problemas.

## Marca

O avatar incluído pertence à organização [pingdotgg](https://github.com/pingdotgg), proprietária do repositório T3 Code.
O projecto deste launcher não é uma distribuição oficial do T3 Code.
