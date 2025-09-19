graph TD

%% === STYLES ===
classDef ui fill:#ADD8E6,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef ssh fill:#90EE90,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef data fill:#FFD700,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef ai fill:#FFB6C1,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef ext fill:#FF69B4,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;

%% === User Interface Layer ===
subgraph "User Interface Layer"
  BanditCLIApp["BanditCLIApp<br/>Main Application Class"]:::ui
  Header["Header Widget"]:::ui
  Footer["Footer Widget"]:::ui
  TabbedContent["Tabbed Content Widget"]:::ui
  TextArea["Text Area Widget"]:::ui
  Input["Input Widget"]:::ui
  Button["Button Widget"]:::ui
  Label["Label Widget"]:::ui

  BanditCLIApp -->|"manages"| Header
  BanditCLIApp -->|"manages"| Footer
  BanditCLIApp -->|"manages"| TabbedContent
  BanditCLIApp -->|"manages"| TextArea
  BanditCLIApp -->|"manages"| Input
  BanditCLIApp -->|"manages"| Button
  BanditCLIApp -->|"manages"| Label
end

%% === SSH Management Layer ===
subgraph "SSH Management Layer"
  SSHConnection["SSHConnection<br/>Manages Single SSH Session"]:::ssh
  SSHManager["SSHManager<br/>Manages Multiple SSH Sessions"]:::ssh

  BanditCLIApp -->|"creates SSH session"| SSHManager
  SSHManager -->|"creates"| SSHConnection
end

%% === Level Data Layer ===
subgraph "Level Data Layer"
  BanditLevelInfo["BanditLevelInfo<br/>Handles Level Data"]:::data

  BanditCLIApp -->|"loads level data"| BanditLevelInfo
end

%% === AI Mentoring Layer ===
subgraph "AI Mentoring Layer"
  BanditAIMentor["BanditAIMentor<br/>Generates Hints and Guidance"]:::ai

  BanditCLIApp -->|"requests AI guidance"| BanditAIMentor
end

%% === External Dependencies ===
subgraph "External Dependencies"
  Paramiko["Paramiko<br/>SSH Client Library"]:::ext
  OpenAI["OpenAI API<br/>Generates AI Responses"]:::ext
  Dotenv["Dotenv<br/>Loads Environment Variables"]:::ext
  BanditLevelsJSON["bandit_levels.json<br/>Static Level Data"]:::ext

  SSHManager -->|"uses"| Paramiko
  BanditAIMentor -->|"uses"| OpenAI
  BanditAIMentor -->|"loads config"| Dotenv
  BanditLevelInfo -->|"loads data from"| BanditLevelsJSON
end

%% === User Interaction Flow ===
User(("User")) -->|"interacts with"| BanditCLIApp
User -->|"connects via SSH"| SSHManager
User -->|"executes commands"| SSHConnection
User -->|"navigates levels"| BanditLevelInfo
User -->|"asks for hints"| BanditAIMentor

%% === Data and Control Flow ===
SSHConnection -->|"sends commands"| SSHManager
SSHManager -->|"returns output"| BanditCLIApp
BanditLevelInfo -->|"provides level info"| BanditCLIApp
BanditAIMentor -->|"returns hints"| BanditCLIApp