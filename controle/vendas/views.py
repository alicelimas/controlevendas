from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cliente, Venda, Parcela
from django.db.models import Sum, Count, Q
from datetime import timedelta, date, datetime
from decimal import Decimal
from django.core.paginator import Paginator
from dateutil.relativedelta import relativedelta  # Novo import
from calendar import monthrange  # Novo import

# Função auxiliar para calcular vencimentos
def calcular_vencimentos(data_base, num_parcelas):
    vencimentos = []
    dia_base = data_base.day
    for i in range(num_parcelas):
        # Avançar i meses a partir da data base
        nova_data = data_base + relativedelta(months=i)
        # Obter o número de dias no mês da nova data
        _, ultimo_dia_mes = monthrange(nova_data.year, nova_data.month)
        # Ajustar o dia para o menor entre dia_base e ultimo_dia_mes
        dia_ajustado = min(dia_base, ultimo_dia_mes)
        # Criar nova data com o dia ajustado
        nova_data = nova_data.replace(day=dia_ajustado)
        vencimentos.append(nova_data)
    return vencimentos

def calcular_parcelas_cliente(cliente, vendas, vencimento_base, maior_parcelas):
    # Lista para armazenar todas as parcelas individuais
    parcelas_por_venda = []

    # Para cada venda, calcular as parcelas individuais
    for venda in vendas:
        valor_parcela = venda.valor / venda.parcelas if venda.parcelas > 0 else 0
        vencimentos = calcular_vencimentos(venda.vencimento, venda.parcelas)
        for i in range(venda.parcelas):
            parcelas_por_venda.append({
                'venda': venda,
                'numero': i + 1,
                'valor': valor_parcela,
                'vencimento': vencimentos[i]
            })

    # Agrupar parcelas por vencimento (considerando o mesmo mês/ano)
    parcelas_agrupadas = {}
    for parcela in parcelas_por_venda:
        vencimento_key = parcela['vencimento'].strftime('%Y-%m')  # Agrupar por ano e mês
        if vencimento_key not in parcelas_agrupadas:
            parcelas_agrupadas[vencimento_key] = {
                'vencimento': parcela['vencimento'],
                'valor_total': Decimal('0.00'),
                'numero': len(parcelas_agrupadas) + 1
            }
        parcelas_agrupadas[vencimento_key]['valor_total'] += parcela['valor']

    # Converter para lista ordenada por vencimento
    parcelas_ordenadas = sorted(parcelas_agrupadas.values(), key=lambda x: x['vencimento'])

    # Determinar parcelas pagas com base nos créditos
    creditos_total = vendas.aggregate(Sum('creditos'))['creditos__sum'] or 0
    valor_total = vendas.aggregate(Sum('valor'))['valor__sum'] or 0
    parcelas_pagas = 0
    if maior_parcelas > 0 and valor_total > 0:
        valor_parcela_media = valor_total / maior_parcelas
        parcelas_pagas = int(creditos_total / valor_parcela_media) if valor_parcela_media > 0 else 0
        if creditos_total > 0 and parcelas_pagas == 0:
            parcelas_pagas = 1
        if parcelas_pagas > maior_parcelas:
            parcelas_pagas = maior_parcelas

    # Criar objetos Parcela
    Parcela.objects.filter(cliente=cliente).delete()  # Limpar parcelas antigas
    parcelas = []
    for i, parcela_info in enumerate(parcelas_ordenadas[:maior_parcelas]):  # Limitar ao maior número de parcelas
        parcela = Parcela(
            cliente=cliente,
            numero=i + 1,
            valor=parcela_info['valor_total'],
            vencimento=parcela_info['vencimento'],
            status='Paga' if i < parcelas_pagas else 'Pendente'
        )
        parcela.save()
        parcelas.append(parcela)

    return parcelas

def cadastrar_cliente(request):
    if request.method == 'POST':
        try:
            nome = request.POST.get('nome')
            sobrenome = request.POST.get('sobrenome')
            contato = request.POST.get('contato')
            cliente = Cliente.objects.create(nome=nome, sobrenome=sobrenome, contato=contato)
            messages.success(request, f'Cliente {cliente} cadastrado com sucesso!')
            return redirect('gerenciar_clientes')  # Redireciona para gerenciar_clientes
        except ValueError:
            messages.error(request, 'Dados inválidos. Verifique os valores inseridos.')
            return redirect('gerenciar_clientes')
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar cliente: {str(e)}')
            return redirect('gerenciar_clientes')
    return render(request, 'cadastrar_cliente.html') 

def gerenciar_clientes(request):
    # Obter termo de busca da query string
    query = request.GET.get('q', '').strip()
    
    # Filtrar clientes com base na busca
    clientes = Cliente.objects.all()
    if query:
        clientes = clientes.filter(
            Q(nome__icontains=query) |
            Q(sobrenome__icontains=query) |
            Q(contato__icontains=query)
        )
    
    # Ordenar alfabeticamente por nome e sobrenome
    clientes = clientes.order_by('nome', 'sobrenome')
    
    # Configurar paginação (15 clientes por página)
    paginator = Paginator(clientes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,  # Passar o termo de busca para o template
    }
    return render(request, 'gerenciar_clientes.html', context)

def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        try:
            cliente.nome = request.POST.get('nome')
            cliente.sobrenome = request.POST.get('sobrenome')
            cliente.contato = request.POST.get('contato')
            cliente.save()
            messages.success(request, f'Cliente {cliente.nome} {cliente.sobrenome} atualizado com sucesso!')
            return redirect('gerenciar_clientes')
        except ValueError:
            messages.error(request, 'Dados inválidos. Verifique os valores inseridos.')
            return redirect('gerenciar_clientes')
    return redirect('gerenciar_clientes')

def excluir_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        try:
            if Venda.objects.filter(cliente=cliente).exists():
                messages.error(request, f'Não é possível excluir {cliente.nome} {cliente.sobrenome} pois há vendas associadas.')
                return redirect('gerenciar_clientes')
            cliente.delete()
            messages.success(request, f'Cliente {cliente.nome} {cliente.sobrenome} excluído com sucesso!')
            return redirect('gerenciar_clientes')
        except Exception as e:
            messages.error(request, f'Erro ao excluir cliente: {str(e)}')
            return redirect('gerenciar_clientes')
    return redirect('gerenciar_clientes')

def registrar_venda(request):
    if request.method == 'POST':
        try:
            cliente = Cliente.objects.get(id=request.POST.get('cliente'))
            valor = Decimal(request.POST.get('valor'))
            parcelas = int(request.POST.get('parcelas'))
            data_compra = datetime.strptime(request.POST.get('data_compra'), '%Y-%m-%d').date()
            vencimento = datetime.strptime(request.POST.get('vencimento'), '%Y-%m-%d').date()

            venda = Venda(
                cliente=cliente,
                produto=request.POST.get('produto'),
                valor=valor,
                parcelas=parcelas,
                data_compra=data_compra,
                vencimento=vencimento,
                saldo_devedor=valor,
                creditos=Decimal('0.00')
            )
            venda.save()

            # Calcular totais do cliente
            vendas_cliente = Venda.objects.filter(cliente=cliente)
            maior_parcelas = vendas_cliente.order_by('-parcelas').first().parcelas
            saldo_devedor_total = vendas_cliente.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or 0

            # Calcular parcelas combinadas
            calcular_parcelas_cliente(cliente, vendas_cliente, vencimento, maior_parcelas)

            messages.success(request, f'Venda registrada! Saldo total do cliente {cliente}: R$ {saldo_devedor_total:.2f}')
            return redirect('dashboard')
        except Cliente.DoesNotExist:
            messages.error(request, 'Cliente não encontrado.')
            return redirect('dashboard')
        except ValueError:
            messages.error(request, 'Dados inválidos. Verifique os valores inseridos.')
            return redirect('dashboard')

    clientes = Cliente.objects.all().order_by('nome', 'sobrenome')
    return render(request, 'venda.html', {'clientes': clientes})

def atualizar_pagamento(request):
    if request.method == 'POST':
        try:
            cliente = Cliente.objects.get(id=request.POST.get('cliente'))
            valor_pago = Decimal(request.POST.get('valor_pago', '0.00'))

            if valor_pago <= 0:
                messages.error(request, 'O valor pago deve ser maior que zero.')
                return redirect('dashboard')

            vendas = Venda.objects.filter(cliente=cliente)
            if not vendas.exists():
                messages.error(request, 'Nenhuma venda encontrada para este cliente.')
                return redirect('dashboard')

            # Distribuir o pagamento proporcionalmente entre as vendas
            saldo_devedor_total = vendas.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or 0
            if saldo_devedor_total <= 0:
                messages.error(request, 'Nenhum saldo devedor para atualizar.')
                return redirect('dashboard')

            pagamento_restante = valor_pago
            for venda in vendas:
                if pagamento_restante > 0 and venda.saldo_devedor > 0:
                    credito_aplicado = min(pagamento_restante, venda.saldo_devedor)
                    venda.creditos += credito_aplicado
                    venda.saldo_devedor -= credito_aplicado
                    venda.save()
                    pagamento_restante -= credito_aplicado

            # Calcular totais do cliente após pagamento
            vendas_cliente = Venda.objects.filter(cliente=cliente)
            maior_parcelas = vendas_cliente.order_by('-parcelas').first().parcelas
            saldo_devedor_total = vendas_cliente.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or 0
            vencimento_base = min([v.vencimento for v in vendas_cliente])  # Menor vencimento das vendas

            # Calcular parcelas combinadas
            calcular_parcelas_cliente(cliente, vendas_cliente, vencimento_base, maior_parcelas)

            messages.success(request, f'Pagamento de R$ {valor_pago:.2f} registrado! Saldo restante do cliente: R$ {saldo_devedor_total:.2f}.')
            return redirect('dashboard')

        except Cliente.DoesNotExist:
            messages.error(request, 'Cliente não encontrado.')
            return redirect('dashboard')
        except ValueError:
            messages.error(request, 'Valor pago inválido.')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Erro ao registrar pagamento: {str(e)}')
            return redirect('dashboard')

    clientes = Cliente.objects.all().order_by('nome', 'sobrenome')
    return render(request, 'pagamento.html', {'clientes': clientes})

def dashboard(request):
    cliente_id = request.GET.get('cliente')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Querysets
    vendas = Venda.objects.select_related('cliente').order_by('-data_compra')[:5]  # 5 vendas mais recentes
    parcelas = Parcela.objects.select_related('cliente').order_by('vencimento', 'numero')[:5]
    clientes = Cliente.objects.all().order_by('nome', 'sobrenome')

    # Totais gerais
    total_clientes = Cliente.objects.count()
    total_a_receber = Venda.objects.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or 0
    parcelas_vencidas = Parcela.objects.filter(status='Pendente', vencimento__lt=date.today()).count()

    # Totais por cliente
    totais = Venda.objects.values('cliente__nome', 'cliente__sobrenome').annotate(total=Sum('saldo_devedor'))
    if cliente_id:
        totais = totais.filter(cliente__id=cliente_id)
    if data_inicio:
        totais = totais.filter(data_compra__gte=data_inicio)
    if data_fim:
        totais = totais.filter(data_compra__lte=data_fim)

    # Paginação (10 clientes por página)
    paginator = Paginator(totais, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'vendas': vendas,
        'page_obj': page_obj,
        'parcelas': parcelas,
        'total_clientes': total_clientes,
        'total_a_receber': total_a_receber,
        'parcelas_vencidas': parcelas_vencidas,
        'clientes': clientes,
        'cliente_id': cliente_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'dashboard.html', context)

def editar_venda(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id)
    if request.method == 'POST':
        try:
            # Atualizar os dados da venda
            venda.produto = request.POST.get('produto')
            venda.valor = Decimal(request.POST.get('valor'))
            venda.parcelas = int(request.POST.get('parcelas'))
            venda.data_compra = datetime.strptime(request.POST.get('data_compra'), '%Y-%m-%d').date()
            venda.vencimento = datetime.strptime(request.POST.get('vencimento'), '%Y-%m-%d').date()
            venda.creditos = Decimal(request.POST.get('creditos'))

            # Garantir consistência: saldo_devedor = valor - creditos
            venda.saldo_devedor = venda.valor - venda.creditos
            venda.save()

            # Calcular totais do cliente
            cliente = venda.cliente
            vendas_cliente = Venda.objects.filter(cliente=cliente)
            maior_parcelas = vendas_cliente.order_by('-parcelas').first().parcelas if vendas_cliente.exists() else 0
            saldo_devedor_total = vendas_cliente.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or 0
            vencimento_base = min([v.vencimento for v in vendas_cliente]) if vendas_cliente.exists() else venda.vencimento

            # Calcular parcelas combinadas
            calcular_parcelas_cliente(cliente, vendas_cliente, vencimento_base, maior_parcelas)

            messages.success(request, f'Venda de {venda.produto} atualizada com sucesso! Saldo total do cliente: R$ {saldo_devedor_total:.2f}.')

            # Redirecionar com base na origem
            origem = request.POST.get('origem', 'dashboard')
            if origem == 'historico':
                query_params = []
                if request.POST.get('cliente'):  # Alinhar com nome do filtro
                    query_params.append(f'cliente={request.POST.get("cliente")}')
                if request.POST.get('data_inicio'):
                    query_params.append(f'data_inicio={request.POST.get("data_inicio")}')
                if request.POST.get('data_fim'):
                    query_params.append(f'data_fim={request.POST.get("data_fim")}')
                redirect_url = '/historico/' + ('?' + '&'.join(query_params) if query_params else '')
                return redirect(redirect_url)
            return redirect('dashboard')

        except ValueError:
            messages.error(request, 'Dados inválidos. Verifique os valores inseridos.')
        except Exception as e:
            messages.error(request, f'Erro ao editar venda: {str(e)}')

        # Em caso de erro, redirecionar para a origem
        origem = request.POST.get('origem', 'dashboard')
        if origem == 'historico':
            query_params = []
            if request.POST.get('cliente'):
                query_params.append(f'cliente={request.POST.get("cliente")}')
            if request.POST.get('data_inicio'):
                query_params.append(f'data_inicio={request.POST.get("data_inicio")}')
            if request.POST.get('data_fim'):
                query_params.append(f'data_fim={request.POST.get("data_fim")}')
            redirect_url = '/historico/' + ('?' + '&'.join(query_params) if query_params else '')
            return redirect(redirect_url)
        return redirect('dashboard')

    return redirect('dashboard')

def excluir_venda(request, venda_id):
    venda = get_object_or_404(Venda, id=venda_id)
    if request.method == 'POST':
        try:
            cliente = venda.cliente
            venda.delete()

            # Calcular totais do cliente após exclusão
            vendas_cliente = Venda.objects.filter(cliente=cliente)
            if vendas_cliente.exists():
                maior_parcelas = vendas_cliente.order_by('-parcelas').first().parcelas
                saldo_devedor_total = vendas_cliente.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or 0
                vencimento_base = vendas_cliente.order_by('vencimento').first().vencimento

                # Calcular parcelas combinadas
                calcular_parcelas_cliente(cliente, vendas_cliente, vencimento_base, maior_parcelas)
            else:
                # Se não há mais vendas, limpar parcelas do cliente
                Parcela.objects.filter(cliente=cliente).delete()
                saldo_devedor_total = 0

            messages.success(request, f'Venda excluída com sucesso!')

            # Redirecionar com base na origem
            origem = request.POST.get('origem', 'dashboard')
            if origem == 'historico':
                query_params = []
                if request.POST.get('cliente'):
                    query_params.append(f'cliente={request.POST.get("cliente")}')
                if request.POST.get('data_inicio'):
                    query_params.append(f'data_inicio={request.POST.get("data_inicio")}')
                if request.POST.get('data_fim'):
                    query_params.append(f'data_fim={request.POST.get("data_fim")}')
                redirect_url = '/historico/' + ('?' + '&'.join(query_params) if query_params else '')
                return redirect(redirect_url)
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'Erro ao excluir venda: {str(e)}')
            origem = request.POST.get('origem', 'dashboard')
            if origem == 'historico':
                query_params = []
                if request.POST.get('cliente'):
                    query_params.append(f'cliente={request.POST.get("cliente")}')
                if request.POST.get('data_inicio'):
                    query_params.append(f'data_inicio={request.POST.get("data_inicio")}')
                if request.POST.get('data_fim'):
                    query_params.append(f'data_fim={request.POST.get("data_fim")}')
                redirect_url = '/historico/' + ('?' + '&'.join(query_params) if query_params else '')
                return redirect(redirect_url)
            return redirect('dashboard')

    return redirect('dashboard')

def historico(request):
    # Obter filtros
    cliente_id = request.GET.get('cliente')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    # Tratar "None" ou None como vazio
    if data_inicio in ('None', None, ''):
        data_inicio = None
    if data_fim in ('None', None, ''):
        data_fim = None

    # Inicializar querysets com otimização
    vendas = Venda.objects.select_related('cliente').all().order_by('-data_compra')
    parcelas = Parcela.objects.select_related('cliente').all().order_by('vencimento', 'numero')
    clientes = Cliente.objects.all().order_by('nome', 'sobrenome')

    # Aplicar filtros
    if cliente_id:
        vendas = vendas.filter(cliente__id=cliente_id)
        parcelas = parcelas.filter(cliente__id=cliente_id)
        clientes = clientes.filter(id=cliente_id)
    if data_inicio:
        vendas = vendas.filter(data_compra__gte=data_inicio)
        parcelas = parcelas.filter(vencimento__gte=data_inicio)
    if data_fim:
        vendas = vendas.filter(data_compra__lte=data_fim)
        parcelas = parcelas.filter(vencimento__lte=data_fim)

    # Agrupar vendas e parcelas por cliente
    agrupamento = []
    for cliente in clientes:
        vendas_cliente = vendas.filter(cliente=cliente)
        parcelas_cliente = parcelas.filter(cliente=cliente)
        if vendas_cliente.exists() or parcelas_cliente.exists():
            agrupamento.append({
                'cliente': cliente,
                'vendas': vendas_cliente,
                'parcelas': parcelas_cliente,
                'total_vendas': vendas_cliente.aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00'),
                'total_saldo_devedor': vendas_cliente.aggregate(Sum('saldo_devedor'))['saldo_devedor__sum'] or Decimal('0.00'),
                'total_parcelas_pendentes': parcelas_cliente.filter(status='Pendente').aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00'),
            })

    
    paginator = Paginator(agrupamento, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'clientes': Cliente.objects.all().order_by('nome', 'sobrenome'),
        'cliente_id': cliente_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'historico.html', context)