from django.db import models

class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    contato = models.CharField(max_length=100)  # Pode ser telefone ou e-mail
    def __str__(self): return f"{self.nome} {self.sobrenome}"

class Venda(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    produto = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    parcelas = models.IntegerField()
    data_compra = models.DateField()
    vencimento = models.DateField()
    creditos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_devedor = models.DecimalField(max_digits=10, decimal_places=2)

class Parcela(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    numero = models.IntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    vencimento = models.DateField()
    status = models.CharField(max_length=20, default='Pendente')