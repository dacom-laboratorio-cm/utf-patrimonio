# Regra de Negócio - Conferência Patrimonial

## Tratamento de Itens Desconhecidos

### Problema
Durante a conferência patrimonial, podem surgir itens cujo tombo não está cadastrado no banco de dados. Isso ocorre quando:

1. **Item novo** - Patrimônio adquirido recentemente, ainda não importado
2. **Item de outro setor** - Patrimônio que deveria estar em outro local
3. **Erro de digitação** - Tombo digitado incorretamente

### Solução Implementada

Quando um item desconhecido é identificado:

1. **Criação automática em ItemPatrimonio**
   - Cria novo registro com tombo identificado
   - Preenche descrição fornecida pelo usuário
   - Define local como o local da conferência
   - Marca observação: "Item identificado em conferência manual"
   - Define valor padrão: "0"

2. **Registro em ConferenciaPatrimonialItem**
   - Vincula ao ItemPatrimonio recém-criado via `item_patrimonio_id`
   - Marca inconsistência como `'item_novo'`
   - Permite rastreamento e auditoria

### Estados de Inconsistência

- **`ok`** - Item encontrado no local correto
- **`local_divergente`** - Item encontrado, mas cadastrado em outro local
- **`item_novo`** - Item encontrado mas não cadastrado (criado automaticamente)
- **`nao_encontrado`** - Item cadastrado mas não encontrado fisicamente
- **`sem_etiqueta`** - Item físico sem plaqueta de identificação

### Integridade Referencial

- Todos os itens com tombo **devem** ter registro em `ItemPatrimonio`
- `ConferenciaPatrimonialItem` referencia `ItemPatrimonio` via FK
- Itens sem etiqueta não criam `ItemPatrimonio` (`item_patrimonio_id=NULL`)

### Fluxo de Dados

```
Conferência Manual
       ↓
Tombo desconhecido detectado
       ↓
Cria ItemPatrimonio (novo)
       ↓
Cria ConferenciaPatrimonialItem → FK para ItemPatrimonio
       ↓
Salva no banco com status 'item_novo'
```

### Benefícios

1. **Rastreabilidade** - Todos os itens ficam registrados
2. **Auditoria** - Histórico de quando/como foi identificado
3. **Gestão** - Facilita regularização posterior
4. **Integridade** - Mantém relações consistentes no banco
