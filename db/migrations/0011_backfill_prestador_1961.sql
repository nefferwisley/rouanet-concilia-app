-- ============================================================
-- 0011 — backfill de PRESTADOR e RAZÃO SOCIAL do projeto 1961
--
-- Gerado por backend/scripts/importar_prestador_planilha.py a partir de
-- 1961_Revisao_Financeira_ATUALIZADA.xlsx (aba "CONCILIAÇÃO REVISADA",
-- 179 lançamentos). Vem como migration em vez de script solto para ficar
-- versionado, reproduzível e com procedência registrada.
--
-- O casamento roda AQUI DENTRO, via row_number() dos dois lados sobre
-- (data, valor): quando o mesmo par se repete (11 casos, ex.: 4 passagens
-- da Gol de mesmo valor no mesmo dia), a n-ésima linha da planilha casa
-- com a n-ésima transação, em ordem estável. Linha da planilha sem
-- transação correspondente não atualiza nada — nunca é adivinhada.
--
-- coalesce() em toda atribuição: reaplicar é seguro e nada já preenchido
-- é sobrescrito por nulo.
-- ============================================================



with planilha (data, valor, seq, prestador, razao_social) as (
  values
    ('2022-11-04'::date, 11000.00::numeric, 1, 'Mônica Guimarães', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2022-11-04'::date, 5000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2022-11-04'::date, 20000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2022-11-04'::date, 30000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2022-11-10'::date, 1200.00::numeric, 1, 'Felipe Frico Guimarães', 'FELIPE GUIMARÃES ROSA'),
    ('2022-11-10'::date, 1200.00::numeric, 2, 'Luis Felipe Labaki', 'LUIS FELIPE LABAKI'),
    ('2022-11-21'::date, 800.00::numeric, 1, 'Luis Felipe Cipullo', 'LUIS FELIPE MONTE CIPULLO'),
    ('2022-11-28'::date, 20000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2022-12-12'::date, 30000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2022-12-14'::date, 6000.00::numeric, 1, 'Júlia Sousa', 'JULIA BARBARA MELO DE SOUSA.'),
    ('2022-12-14'::date, 2000.00::numeric, 1, 'Lia Pini', 'PLANIFILMES LTDA.'),
    ('2022-12-20'::date, 20000.00::numeric, 1, 'Circunstância Cinematográfica', 'CIRCUNSTÂNCIA CINEMATOGRÁFICA'),
    ('2023-01-23'::date, 30000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2023-01-23'::date, 4500.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2023-02-22'::date, 19550.00::numeric, 1, 'Amir Labaki', 'Amir Labaki'),
    ('2023-07-03'::date, 25000.00::numeric, 1, 'Amir Labaki', 'CIRCUNSTANCIA CINEMATOGRAF.'),
    ('2023-07-03'::date, 25000.00::numeric, 2, 'Mônica Guimarães', 'MOG PRODUTORA'),
    ('2023-08-18'::date, 380.00::numeric, 1, 'Bandeirantes', 'RADIO E TELEVISAO BANDEIRANTES'),
    ('2023-08-25'::date, 10500.00::numeric, 1, 'Eloa Chouzal (primeira parcela)', 'MEMORIA COLETIVA IMAGENS'),
    ('2023-09-04'::date, 700.00::numeric, 1, 'Porviroscopio Projetos', 'PORVIROSCOPIO PROJETOS'),
    ('2023-09-05'::date, 33000.00::numeric, 1, 'Fogo Filmes - André Finotti (primeira parcela)', 'FOGO FILMES LTDA'),
    ('2023-09-05'::date, 120.00::numeric, 1, 'Guia de Arrecadação - Governo RS', 'GA - ITCD/TXS GOV RS (Impostos)'),
    ('2023-09-06'::date, 4900.00::numeric, 1, 'Júlia Sousa', 'Júlia Sousa'),
    ('2023-09-11'::date, 3000.00::numeric, 1, 'Beatriz Pomar', 'ANA BEATRIZ HERMANSON POMAR'),
    ('2023-09-20'::date, 2870.87::numeric, 1, 'André Manfrin (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 2870.87::numeric, 2, 'Luis Cipullo (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 2870.87::numeric, 3, 'Thiago Cunha (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 2870.87::numeric, 4, 'Frico Guimarães (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 1524.64::numeric, 1, 'André Manfrin (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 1524.64::numeric, 2, 'Luis Cipullo (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 1524.64::numeric, 3, 'Frico Guimarães (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-20'::date, 1524.64::numeric, 4, 'Thiago Cunha (passagem aérea)', 'GOL Linhas Aéreas'),
    ('2023-09-26'::date, 10000.00::numeric, 1, 'Mônica Guimarães', 'Mônica Guimarães'),
    ('2023-09-26'::date, 11250.00::numeric, 1, 'André Manfrim', 'André Manfrim'),
    ('2023-09-26'::date, 3000.00::numeric, 1, 'Camila Braune', 'Camila Braune'),
    ('2023-09-28'::date, 350.00::numeric, 1, 'Casa do Rodie', 'CASA DO ROADIE'),
    ('2023-09-28'::date, 1000.00::numeric, 1, 'Sofia Vontobel', 'SOFIA VONTOBEL BACCARINI'),
    ('2023-09-28'::date, 1000.00::numeric, 2, 'André Manfrim', 'ANDRÉ LIMA MANFRIM'),
    ('2023-09-28'::date, 15.30::numeric, 1, 'Casa do Rodie', 'CASA DO ROADIE'),
    ('2023-09-28'::date, 8800.00::numeric, 1, 'Hospedagem equipe', 'CITYHOME SERVICOS IMOBILIARIOS'),
    ('2023-09-29'::date, 5768.40::numeric, 1, 'Hospedagem AL e MG', 'PATEO MOINHOS DE VENTO ADM'),
    ('2023-09-29'::date, 500.00::numeric, 1, 'Hospedagem AL (cityhome)', 'CITYHOME SERVICOS IMOBILIARIOS'),
    ('2023-09-29'::date, 35000.00::numeric, 1, 'MR5  (equipamentos de foto)', 'MARTINA MILLA RAFFAELLI ME (MR5)'),
    ('2023-09-29'::date, 3116.00::numeric, 1, 'Hds Externos', 'MATRON INFORMATICA'),
    ('2023-09-29'::date, 1050.00::numeric, 1, 'Luis Cipullo', 'LUIS FELIPE MONTE CIPULLO'),
    ('2023-09-29'::date, 1050.00::numeric, 2, 'Frico Guimarães', 'Felipe Guimarães Rosa'),
    ('2023-09-29'::date, 1050.00::numeric, 3, 'Thiago Cunha', 'FELIPE GUIMARÃES ROSA'),
    ('2023-09-29'::date, 560.00::numeric, 1, 'Sofia Vontobel', 'SOFIA VONTOBEL BACCARINI'),
    ('2023-09-29'::date, 560.00::numeric, 2, 'Fabio Baltar', 'Fábio Baltar Duarte'),
    ('2023-09-29'::date, 1050.00::numeric, 4, 'André Manfrim', 'Andre Lima Monfrini'),
    ('2023-09-29'::date, 150.00::numeric, 1, 'Hospedagem AL - complemento (cityhome)', 'CITYHOME SERVICOS IMOBILIARIOS'),
    ('2023-09-29'::date, 35.10::numeric, 1, 'Correios', 'SCM PREST SERV POSTAIS'),
    ('2023-10-02'::date, 1610.00::numeric, 1, 'Hospedagem AL', 'PATEO MOINHOS DE VENTO ADM'),
    ('2023-10-03'::date, 200.00::numeric, 1, 'Motorista POA', 'Glademir Martins Machado'),
    ('2023-10-03'::date, 3020.00::numeric, 1, 'Hds Externos', 'Hds Externos'),
    ('2023-10-05'::date, 700.00::numeric, 1, 'Motorista SP', '1º Pix rejeitado e reenviado no mesmo dia (líquido R$ 700,00) Favorecido no extrato: EDSON DE CAMARGO TRANSPORTES.'),
    ('2023-10-05'::date, 500.00::numeric, 1, 'Amir Labaki', 'AMIR LABAKI'),
    ('2023-10-06'::date, 10500.00::numeric, 1, 'Eloa Chouzal  (parcela final)', 'MEMORIA COLETIVA IMAGENS'),
    ('2023-10-09'::date, 136.69::numeric, 1, 'Amir Labaki_reembolso', 'Pago em um único Pix de R$ 945,49 junto com a outra linha do controle 59 (136,69 + 808,80). Pix único de R$ 945,49'),
    ('2023-10-09'::date, 808.80::numeric, 1, 'Amir Labaki_reembolso', 'Pago em um único Pix de R$ 945,49 junto com a outra linha do controle 59 (136,69 + 808,80). Pix único de R$ 945,49'),
    ('2023-10-09'::date, 13500.00::numeric, 1, 'Frico Guimarães - parcela 1', 'MOG PRODUTORA'),
    ('2023-10-09'::date, 7500.00::numeric, 1, 'Luis Cipullo - parcela 1', 'LUIS FELIPE MONTE CIPULLO'),
    ('2023-10-09'::date, 4800.00::numeric, 1, 'Thiago Cunha - parcela 1', 'THIAGO AUGUSTO GOMAS CUNHA'),
    ('2023-10-09'::date, 1800.00::numeric, 1, 'Fabio Baltar', 'FÁBIO BALTAR DUARTE'),
    ('2023-10-09'::date, 1800.01::numeric, 1, 'Fabio Baltar', 'FÁBIO BALTAR DUARTE'),
    ('2023-10-09'::date, 9502.77::numeric, 1, 'Mandala Tour', 'MANDALA TOURS'),
    ('2023-10-09'::date, 240.00::numeric, 1, 'Luis Cipullo', 'LUIS FELIPE MONTE CIPULLO'),
    ('2023-10-09'::date, 240.00::numeric, 2, 'André Manfrim', 'Andre Lima Monfrini'),
    ('2023-10-09'::date, 240.00::numeric, 3, 'Frico Guimarães', 'Felipe Guimarães Rosa'),
    ('2023-10-09'::date, 240.00::numeric, 4, 'Thiago Cunha', 'ANDRE LIMA MONFRINI'),
    ('2023-10-10'::date, 500.00::numeric, 1, 'André Manfrim_verba de produção', 'Andre Lima Monfrini'),
    ('2023-10-10'::date, 2300.00::numeric, 1, 'FAU_locação de espaço', 'CONTA RECEITAS D F'),
    ('2023-10-11'::date, 1500.00::numeric, 1, 'Beatriz Pomar', 'ANA BEATRIZ HERMANSON POMAR'),
    ('2023-10-11'::date, 400.00::numeric, 1, 'Mac Porto Alegre', 'AAMAC'),
    ('2023-10-11'::date, 500.00::numeric, 1, 'Motorista SP', 'Malnes Transporte e Produções'),
    ('2023-10-11'::date, 4000.00::numeric, 1, 'Sofia Vontobel', 'VONDOC FILMES LTDA'),
    ('2023-10-11'::date, 1000.00::numeric, 1, 'Ida Leal_verba RJ', 'IDALINA SOUZA RIBEIRO'),
    ('2023-10-11'::date, 9672.00::numeric, 1, 'Hotel equipe (RJ)', 'MANDALA TOURS'),
    ('2023-10-13'::date, 1200.00::numeric, 1, 'André Manfrim_verba alimentação', 'Andre Lima Monfrini'),
    ('2023-10-13'::date, 1200.00::numeric, 2, 'Frico Guimarães_verba alimentação', 'Felipe Guimarães Rosa'),
    ('2023-10-13'::date, 1200.00::numeric, 3, 'Luis Cipullo_verba alimentação', 'ANDRE LIMA MONFRINI'),
    ('2023-10-13'::date, 1200.00::numeric, 4, 'Thiago Cunha_verba alimentação', 'FELIPE GUIMARÃES ROSA'),
    ('2023-10-13'::date, 1000.00::numeric, 1, 'André Manfrim_verba de produção RJ', 'ANDRÉ LIMA MANFRIM'),
    ('2023-10-13'::date, 480.00::numeric, 1, 'Ida Leal_verba de alimentação', 'IDALINA SOUZA RIBEIRO'),
    ('2023-10-13'::date, 480.00::numeric, 2, 'Anne Santos_verba de alimentação', 'IDALINA SOUZA RIBEIRO'),
    ('2023-10-13'::date, 300.00::numeric, 1, 'Alimentação Motorista RJ', 'RICARDO DIAS DOS SANTOS'),
    ('2023-10-13'::date, 2000.00::numeric, 1, 'Ida Leal - Primenra parcela', 'MAGA PROJETOS CULTURAIS'),
    ('2023-10-16'::date, 3000.00::numeric, 1, 'Beatriz Pomar', 'Beatriz Pomar'),
    ('2023-10-16'::date, 1100.00::numeric, 1, 'Equipamento de luz RJ', 'LUZ RIO LOCACAO DE EQUIPAMENTOS'),
    ('2023-10-17'::date, 4375.00::numeric, 1, 'Motorista SP', 'CRISTHIANO RODRIGUES DE JESUS'),
    ('2023-10-17'::date, 4900.00::numeric, 1, 'Motorista POA', 'CLAUDIA'),
    ('2023-10-18'::date, 550.00::numeric, 1, 'Fernando Miguel', 'FERNANDO MIGUEL EFRON'),
    ('2023-10-24'::date, 9427.38::numeric, 1, 'Mônica Guimarães (reembolso)', 'MONICA GUIMARAES P MORAES'),
    ('2023-10-25'::date, 20625.00::numeric, 1, 'André Finotti', 'FOGO FILMES LTDA'),
    ('2023-10-25'::date, 3600.00::numeric, 1, 'Anne Santos - pagamento', 'ANNE SANTOS'),
    ('2023-10-25'::date, 13500.00::numeric, 1, 'Frico Guimarães - parcela final', 'MOG PRODUTORA'),
    ('2023-10-25'::date, 10000.00::numeric, 1, 'Luiz Felipe G Labaki', 'Luiz Felipe G Labaki'),
    ('2023-10-25'::date, 2000.00::numeric, 1, 'Ida Leal - parcela final', 'MAGA PROJETOS CULTURAIS'),
    ('2023-10-25'::date, 1800.00::numeric, 1, 'Thiago Cunha - equipamento', 'THIAGO AUGUSTO GOMAS CUNHA'),
    ('2023-10-25'::date, 4800.00::numeric, 1, 'Thiago Cunha - parcela final', 'THIAGO AUGUSTO GOMAS CUNHA'),
    ('2023-10-25'::date, 816.42::numeric, 1, 'Sofia Vontobel', 'SOFIA VONTOBEL BACCARINI'),
    ('2023-10-25'::date, 450.00::numeric, 1, 'Calendoscopia', 'CALEIDOSKOPICA PRODUCOES'),
    ('2023-10-25'::date, 4500.00::numeric, 1, 'Filmes de Taipa', 'FILMES DE TAIPA PROD'),
    ('2023-10-25'::date, 600.00::numeric, 1, 'Eletrica Cinema', 'ELECTRICA CINEMA E VIDEO (boleto)'),
    ('2023-10-26'::date, 6550.00::numeric, 1, 'Motorista RJ', 'GRIFE RIO LOCADORA LTDA (transferência)'),
    ('2023-10-26'::date, 995.00::numeric, 1, 'Locall POA', 'LOC ALL DE CINEMA E TELEVISAO'),
    ('2023-10-26'::date, 7500.00::numeric, 1, 'Luis Cipullo', 'LUIS FELIPE MONTE CIPULLO'),
    ('2023-10-26'::date, 11250.00::numeric, 1, 'André Manfrim', 'FILMES DE TAIPA PROD'),
    ('2023-10-30'::date, 2529.85::numeric, 1, 'Hotel equipe (diária extra RJ)', 'WINDSOR ADMINISTRACAO DE HOTEIS'),
    ('2023-10-30'::date, 1559.33::numeric, 1, 'Hotel Amir (diária extra RJ)', 'WINDSOR ADMINISTRACAO DE HOTEIS'),
    ('2023-10-30'::date, 450.00::numeric, 1, 'Arthur Rodrigues', '(favorecido não identificado no extrato)'),
    ('2023-10-30'::date, 211.50::numeric, 1, 'Brilho Equipamentos', 'BRILHO'),
    ('2023-10-30'::date, 1500.00::numeric, 1, 'MR5  (equipamentos de foto)', 'MARTINA MILLA RAFFAELLI ME (MR5)'),
    ('2023-10-31'::date, 320.00::numeric, 1, 'Alimentação Motorista RJ', 'JEFFERSON MARCOS SILVA'),
    ('2023-10-31'::date, 1020.00::numeric, 1, 'Frico  alimentação e ajuda de custo', 'Felipe Guimarães Rosa'),
    ('2023-10-31'::date, 1020.00::numeric, 2, 'Luis alimentação e ajuda de custo', 'FELIPE GUIMARÃES ROSA'),
    ('2023-10-31'::date, 1020.00::numeric, 3, 'André alimentação e ajuda de custo', 'Andre Lima Monfrini'),
    ('2023-10-31'::date, 200.00::numeric, 1, 'Verba de produção', 'André Lima Manfrim'),
    ('2023-11-01'::date, 316.23::numeric, 1, 'Late Check-out', 'Late Check-out'),
    ('2023-11-08'::date, 300.00::numeric, 1, 'Bernardo Tavares', '1º Pix rejeitado e reenviado (líquido R$ 300,00)'),
    ('2023-11-08'::date, 4750.00::numeric, 1, 'Van São Paulo x Rio de Janeiro', 'CRISTHIANO RODRIGUES DE JESUS'),
    ('2023-11-14'::date, 27000.00::numeric, 1, 'Mônica Guimarães', 'Mônica Guimarães'),
    ('2023-11-14'::date, 3353.72::numeric, 1, 'Reembolso Mônica Guimarães', 'Reembolso Mônica Guimarães'),
    ('2023-11-14'::date, 371.02::numeric, 1, 'Reembolso Mônica Guimarães', 'Reembolso Mônica Guimarães'),
    ('2023-11-14'::date, 750.00::numeric, 1, 'Bié Cinema e TV', 'Bié Cinema e TV'),
    ('2023-11-14'::date, 400.00::numeric, 1, 'Filmes de Taipa', 'Filmes de Taipa'),
    ('2023-11-27'::date, 20625.00::numeric, 1, 'André Finotti', 'FOGO FILMES LTDA'),
    ('2023-12-11'::date, 2000.00::numeric, 1, 'Eloa Chouzal  (semana adicional)', 'MEMORIA COLETIVA IMAGENS'),
    ('2023-12-20'::date, 585.00::numeric, 1, 'Raquel - diária extra', 'RAQUEL DE OLIVEIRA LAZARO'),
    ('2023-12-20'::date, 20625.00::numeric, 1, 'André Finotti', 'FOGO FILMES LTDA'),
    ('2024-01-24'::date, 20625.00::numeric, 1, 'André Finotti', 'FOGO FILMES LTDA'),
    ('2024-01-31'::date, 487.20::numeric, 1, 'Fp Courrier', 'IN SAMPA COURIER ENTREGAS'),
    ('2024-02-23'::date, 6000.00::numeric, 1, 'Júlia Sousa', 'JUBA PRODUCOES'),
    ('2024-02-23'::date, 22500.00::numeric, 1, 'André Finotti', 'FOGO FILMES'),
    ('2024-05-07'::date, 4000.00::numeric, 1, 'Júlia Sousa', 'JULIA BARBARA MELO DE SOUSA'),
    ('2024-05-31'::date, 5000.00::numeric, 1, 'Estúdio Ganzah', 'GANZAH'),
    ('2024-06-03'::date, 13500.00::numeric, 1, 'André Finotti', 'André Finotti'),
    ('2024-07-03'::date, 5000.00::numeric, 1, 'Giovana Amano', 'Giovana Amano'),
    ('2024-07-30'::date, 8000.00::numeric, 1, 'Wagner Labs Anastacio ME / Brasil Imagem', 'BRASIL IMAGEM'),
    ('2024-08-09'::date, 2815.00::numeric, 1, 'Sylvio Back', 'ANJO AZUL FILMES LTDA (transferência)'),
    ('2024-08-09'::date, 2873.00::numeric, 1, 'Cinemateca', 'Cinemateca'),
    ('2024-08-09'::date, 4000.00::numeric, 1, 'Fabiana Werneck', 'F. WERNECK BARCINSKI LTDA'),
    ('2024-08-09'::date, 550.00::numeric, 1, 'Biblioteca Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-08-16'::date, 130.00::numeric, 1, 'CPD DOC', 'FUNDACAO GETULIO VARGAS (boleto)'),
    ('2024-08-19'::date, 8627.00::numeric, 1, 'Cinemateca', 'SOCIEDADE AMIGOS DA CINEMATECA'),
    ('2024-09-03'::date, 600.00::numeric, 1, 'Camila Braune - Somm adicional Ricupero', 'CAMILA BRAUNE'),
    ('2024-09-05'::date, 938.50::numeric, 1, 'Silvyo Back - O Globo', 'GLOBO COM E PART SA (boleto)'),
    ('2024-09-17'::date, 2250.00::numeric, 1, 'Lapfilme Produções', 'LAPFILME P C LTDA'),
    ('2024-09-17'::date, 2632.45::numeric, 1, 'Estadão', 'S A O ESTADO DE S PAULO'),
    ('2024-09-23'::date, 5500.00::numeric, 1, 'Jornal de Brasil', 'Jornal de Brasil'),
    ('2024-09-25'::date, 6726.23::numeric, 1, 'INA', 'COTACAO D.T.V.M. S/A'),
    ('2024-09-30'::date, 700.00::numeric, 1, 'Biblioteca Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-09-30'::date, 2400.00::numeric, 1, 'Biblioteca Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-10-10'::date, 1836.22::numeric, 1, 'Le monde', 'COTACAO D.T.V.M. S/A'),
    ('2024-10-10'::date, 372.00::numeric, 1, 'Cinemateca Brasileira', 'SOCIEDADE AMIGOS DA CINEMATECA'),
    ('2024-10-31'::date, 5000.00::numeric, 1, 'Iconografia', 'PORVIROSCOPIO PROJETOS'),
    ('2024-10-31'::date, 5500.00::numeric, 1, 'Silvio Tendler', 'CALIBAN PRODUCOES CINEMATOGRAFICAS'),
    ('2024-11-01'::date, 140.00::numeric, 1, 'Biblioteca Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-11-04'::date, 400.00::numeric, 1, 'Arquivo Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-11-08'::date, 600.00::numeric, 1, 'Echos Comunicação', 'ECHO S COMUNICACAO SONORA'),
    ('2024-11-08'::date, 1000.00::numeric, 1, 'Roberto Dávila', 'ROBERTO FERRARETTO D AVILA'),
    ('2024-11-12'::date, 12.00::numeric, 1, 'Biblioteca Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-11-14'::date, 200.00::numeric, 1, 'Arquivo Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2024-11-28'::date, 230.00::numeric, 1, 'Procimar', 'MARACH SERVICOS AUDIOVISUAIS'),
    ('2024-12-05'::date, 6400.00::numeric, 1, 'Correio Brasiliense', 'LIRA PARTICIPACOES E FOMENTO (boleto)'),
    ('2024-12-05'::date, 1500.00::numeric, 1, 'Geisa Kety', 'GEISA DA SILVA DE JESUS'),
    ('2024-12-10'::date, 100.00::numeric, 1, 'FGV', 'FUNDACAO GETULIO VARGAS (boleto)'),
    ('2024-12-17'::date, 3000.00::numeric, 1, 'Fermata - fonograma', 'EDITORA E IMPORTADORA MUSICAL (FERMATA)'),
    ('2024-12-17'::date, 2000.00::numeric, 1, 'Som Livre - fonograma', 'SOM LIVRE'),
    ('2024-12-17'::date, 3500.00::numeric, 1, 'Carlos Lyra Produções - fonograma', 'CARLOS LYRA EDICOES MUSICAIS'),
    ('2024-12-17'::date, 8393.30::numeric, 1, 'NYT', 'COTACAO D.T.V.M. S/A'),
    ('2024-12-26'::date, 5000.00::numeric, 1, 'Giovana Amano', 'GIOVANA AMANO'),
    ('2025-01-16'::date, 50.00::numeric, 1, 'Arquivo Nacional', 'GRU - GUIA RECOLHIMENTO UNIÃO'),
    ('2025-02-03'::date, 975.04::numeric, 1, 'La Nacion', '2 tentativas rejeitadas e estornadas no mesmo dia (líquido R$ 975,04) Favorecido no extrato: BANCO RENDIMENTO S/A.'),
    ('2025-02-27'::date, 7000.00::numeric, 1, 'Marcos Azambuja', 'GANZAH'),
    ('2025-03-25'::date, 626.30::numeric, 1, 'AGENCIA NACIONAL DO CINEMA - ANCINE (boleto)', 'Consta no extrato e não estava na conciliação.'),
    ('2025-04-30'::date, 3000.00::numeric, 1, 'Giovana Amano', 'GIOVANA AMANO'),
    ('2025-04-30'::date, 1200.00::numeric, 1, 'Lia Pini', 'PLANIFILMES LTDA'),
    ('2025-05-07'::date, 18093.63::numeric, 1, 'André Finotti', 'FOGO FILMES')
),
banco as (
  select id, data_pagamento, valor_bruto,
         row_number() over (
           partition by data_pagamento, valor_bruto
           order by created_at, id
         ) as seq
    from transacoes
   where projeto_id = 'a2fe2ae0-4041-47c9-bda1-e347982d0bc2'
)
update transacoes t
   set prestador    = coalesce(p.prestador, t.prestador),
       razao_social = coalesce(p.razao_social, t.razao_social)
  from planilha p
  join banco b
    on b.data_pagamento = p.data
   and b.valor_bruto    = p.valor
   and b.seq            = p.seq
 where t.id = b.id;

-- tipo_pessoa segue o DOCUMENTO, não o nome: 11 dígitos = PF, 14 = PJ.
update transacoes
   set tipo_pessoa = case
         when length(regexp_replace(coalesce(cnpj_fornecedor,''),'\D','','g')) = 11 then 'PF'
         when length(regexp_replace(coalesce(cnpj_fornecedor,''),'\D','','g')) = 14 then 'PJ'
       end
 where projeto_id = 'a2fe2ae0-4041-47c9-bda1-e347982d0bc2'
   and tipo_pessoa is null
   and cnpj_fornecedor is not null;

