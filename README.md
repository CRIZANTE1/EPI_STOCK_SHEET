# EPI Stock Sheet: Gerenciamento Inteligente de Estoque

[![Python Version](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit Version](https://img.shields.io/badge/Streamlit-1.44+-red.svg)](https://streamlit.io)

Uma aplicação web inteligente construída com Streamlit para o gerenciamento de estoque de Equipamentos de Proteção Individual (EPI). Este sistema vai além do simples controle de estoque, integrando a IA Generativa do Google para fornecer recomendações de compra inteligentes, análise de tendências e previsões de consumo.

A aplicação utiliza o Google Sheets como um banco de dados leve e acessível, e garante o acesso através do OIDC (OpenID Connect) do Google para uma experiência de login de usuário segura e simplificada.

---

## 📋 Principais Funcionalidades

*   **🔐 Autenticação Segura:** O login do usuário é gerenciado via Google (OIDC), garantindo acesso seguro e fácil sem a necessidade de gerenciar senhas separadas.
*   **👤 Controle de Acesso por Função:** Diferencia entre usuários padrão (visualização) e administradores (capacidades CRUD completas), com o acesso gerenciado diretamente na planilha do Google Sheets.
*   **📊 Painel Interativo:** Uma visualização limpa e em tempo real de todas as transações de estoque (entradas e saídas) e do status atual do inventário, com gráficos interativos.
*   **⚙️ Operações CRUD Completas:** Administradores podem facilmente Adicionar, Editar e Excluir registros de estoque através de uma interface intuitiva.
*   **🤖 Recomendações com IA:** O sistema analisa o estoque atual, histórico de uso, dados de funcionários e regras específicas de equipamentos (como vida útil) para gerar recomendações de compra inteligentes e baseadas em dados.
*   **📈 Análise Avançada e Previsões:** Uma página de análise dedicada fornece insights sobre tendências de uso, identifica os maiores consumidores e projeta a demanda futura usando previsão de séries temporais.
*   **📄 Backend no Google Sheets:** Utiliza uma planilha do Google como um banco de dados flexível e de fácil gerenciamento, permitindo acesso simples aos dados e backups.

---

## 🚀 Arquitetura do Sistema

A aplicação é construída em torno de uma arquitetura simples, mas poderosa:

1.  **Frontend (Streamlit):** Toda a interface do usuário, desde as páginas de login até os painéis de dados e de administração, é construída com Streamlit.
2.  **Autenticação (Streamlit OIDC):** O suporte nativo do Streamlit para OIDC gerencia o fluxo de login com o Google, autenticando os usuários e fornecendo sua identidade para a aplicação.
3.  **Lógica de Backend (Python/Pandas):** A lógica principal da aplicação, a manipulação de dados e os cálculos são realizados em Python, utilizando a biblioteca Pandas.
4.  **Banco de Dados (Google Sheets):** Todos os dados — transações de estoque, funções de usuário e informações de funcionários — são armazenados e recuperados de um único documento do Google Sheets através da biblioteca `pygsheets`.
5.  **Inteligência (Google Gemini AI):** Para recomendações avançadas, a aplicação constrói um prompt detalhado com dados relevantes e o envia para a API do Google Gemini, retornando insights acionáveis para o usuário.

---

## 🛠️ Configuração e Instalação

Siga estes passos para configurar e executar o projeto localmente.

### Pré-requisitos

*   Python 3.9+
*   Git
*   Um projeto no Google Cloud Platform (GCP)

### 1. Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/EPI_STOCK_SHEET.git
cd EPI_STOCK_SHEET
```

### 2. Configurar um Ambiente Virtual

```bash
# Para macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Para Windows
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Configuração

Esta aplicação requer credenciais para o Google Sheets, Google AI e OIDC.

#### a. Credenciais da API do Google Sheets

1.  Acesse o seu [Google Cloud Console](https://console.cloud.google.com/).
2.  Ative a **Google Drive API** e a **Google Sheets API**.
3.  Crie uma Conta de Serviço (Service Account). Vá para "Credenciais" -> "Criar Credenciais" -> "Conta de Serviço".
4.  Dê um nome à conta de serviço, conceda a ela o papel de "Editor" e conclua.
5.  Abra a conta de serviço recém-criada, vá para a aba "Chaves", clique em "Adicionar Chave" -> "Criar nova chave", e selecione **JSON**. Um arquivo `cred.json` será baixado.
6.  Mova este arquivo baixado para o diretório `credentials/` na raiz do projeto.
7.  **Compartilhe sua Planilha Google** com o `client_email` encontrado dentro do arquivo `cred.json`.

#### b. Chave de API do Google Generative AI

1.  Obtenha uma chave de API no [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Crie um arquivo chamado `.env` na raiz do projeto.
3.  Adicione sua chave de API ao arquivo `.env`:
    ```
    GOOGLE_API_KEY="SUA_CHAVE_DE_API_AQUI"
    ```

#### c. Configuração do Streamlit OIDC (para Login com Google)

1.  No Google Cloud Console, vá para "APIs e Serviços" -> "Credenciais".
2.  Crie um **ID do cliente OAuth 2.0**.
    *   Tipo de aplicação: **Aplicativo da Web**.
    *   URIs de redirecionamento autorizados: Adicione `http://localhost:8501`.
3.  Copie o **ID do Cliente** e o **Segredo do Cliente**.
4.  Crie o arquivo de segredos do Streamlit: `.streamlit/secrets.toml`.
5.  Adicione sua configuração OIDC ao arquivo. **É crucial que a seção seja nomeada `[connections.oidc]`**.

    ```toml
    # .streamlit/secrets.toml

    [connections.oidc]
    google_client_id = "SEU_ID_DE_CLIENTE_GOOGLE"
    google_client_secret = "SEU_SEGREDO_DE_CLIENTE_GOOGLE"
    google_redirect_uri = "http://localhost:8501"
    ```

#### d. Configuração do Documento Google Sheets

Crie uma Planilha Google e certifique-se de que ela tenha as seguintes abas com os nomes exatos:

1.  **`control_stock`**:
    *   Colunas: `id`, `epi_name`, `quantity`, `transaction_type`, `date`, `value`, `requester`, `CA`
2.  **`users`**:
    *   Colunas: `adm_name` (Esta coluna armazena os nomes de exibição dos usuários que devem ter privilégios de administrador).
3.  **`funcionarios`**:
    *   Usada pela IA para entender as necessidades dos funcionários.
    *   Colunas: `Tamanho Camisa Manga Comprida`, `Tamanho Calça`, `Tamanho Jaleco para laboratório`, `Tamanho Camisa Polo`, `Tamanho de Japona de Lã (para frio)`, `Tamanho Jaquetas (para frio)`, `Tamanho do calçado`, `Quantidade de Calças`, etc.
4.  **`empregados`**:
    *   Usada para preencher o menu suspenso "Requisitante".
    *   Colunas: `name_empregado`

### 5. Executar a Aplicação

```bash
streamlit run main.py
```

Abra seu navegador em `http://localhost:8501`.

---

## 📖 Como Usar

1.  **Login:** Clique no botão "Fazer Login com Google" para se autenticar.
2.  **Navegar:** Use a barra lateral para alternar entre a "Página Principal", "Análise e Recomendações" e (para administradores) o "Painel Administrativo".
3.  **Gerenciar Estoque (Admin):** Na página principal, use as seções expansíveis para adicionar, editar ou excluir registros de estoque.
4.  **Gerar Recomendações:** Navegue até a página "Análise e Recomendações" e clique no botão para obter sugestões de compra com tecnologia de IA. Os resultados são salvos em um histórico de sessão.
5.  **Visualizar Análises:** Explore tendências de uso e previsões na página de análise (se integrada ao menu).

### Acesso de Administrador

Para conceder privilégios de administrador a um usuário:
1.  Peça para o usuário fazer login uma vez.
2.  Anote o nome completo dele conforme exibido pelo Google (ex: "Fulano de Tal").
3.  Abra sua Planilha Google, vá para a aba **`users`** e adicione o nome completo dele em uma nova linha sob a coluna `adm_name`.
4.  O usuário terá direitos de administrador em sua próxima sessão.

---

## 📜 Licença

Este projeto possui Licença Restrita.

## ✒️ Autor

*   **Cristian Ferreira Carlos**
*   [Perfil no LinkedIn](https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/)
