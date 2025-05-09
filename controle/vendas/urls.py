from django.urls import path
from . import views

urlpatterns = [
    path('cadastrar-cliente/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('venda/', views.registrar_venda, name='venda'),
    path('pagamento/', views.atualizar_pagamento, name='pagamento'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('editar-venda/<int:venda_id>/', views.editar_venda, name='editar_venda'),
    path('excluir-venda/<int:venda_id>/', views.excluir_venda, name='excluir_venda'),
    path('historico/', views.historico, name='historico'),
     path('gerenciar-clientes/', views.gerenciar_clientes, name='gerenciar_clientes'),
    path('editar-cliente/<int:cliente_id>/', views.editar_cliente, name='editar_cliente'),
    path('excluir-cliente/<int:cliente_id>/', views.excluir_cliente, name='excluir_cliente'),
    path('', views.dashboard, name='home'),  
]