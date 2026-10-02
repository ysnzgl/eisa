with open('apps/abonelik/models.py', encoding='utf-8') as f:
    src = f.read()

old_start = 'class CihazOdemePlani(BaseModel):'
old_end = '    durum = models.CharField(\n        max_length=16, choices=Durum.choices, default=Durum.AKTIF, db_index=True\n    )'

i1 = src.find(old_start)
i2 = src.find(old_end, i1) + len(old_end)
old = src[i1:i2]
print('Found:', len(old), 'chars')
