from django.contrib import admin
from .models import Cliente, Venda, Parcela

# Personalizar a exibição de Cliente
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sobrenome', 'contato')  # Campos exibidos na lista
    search_fields = ('nome', 'sobrenome', 'contato')  # Campos pesquisáveis
    list_filter = ('nome',)  # Filtro lateral por nome

# Personalizar a exibição de Venda
@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'produto', 'valor', 'parcelas', 'data_compra', 'vencimento', 'creditos', 'saldo_devedor')  # Campos exibidos
    search_fields = ('cliente__nome', 'cliente__sobrenome', 'produto')  # Pesquisa por cliente e produto
    list_filter = ('cliente', 'data_compra')  # Filtros por cliente e data
    ordering = ('-data_compra',)  # Ordenar por data decrescente

# Personalizar a exibição de Parcela
@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'numero', 'valor', 'vencimento', 'status')  # Campos exibidos
    search_fields = ('cliente__nome', 'cliente__sobrenome')  # Pesquisa por cliente
    list_filter = ('status', 'vencimento')  # Filtros por status e vencimento
    ordering = ('vencimento',)  # Ordenar por vencimento