module "ceny_towarow_table" {
  source     = "./modules/dynamodb_table"
  table_name = "ceny_towarow"
  hash_key   = "ID_GRUPY_CEN"

  attributes = [
    { name = "ID_GRUPY_CEN", type = "N" },
    { name = "ID_TOWARU", type = "N" },
    { name = "CENA", type = "N" },
    { name = "FLAGA", type = "S" },
    { name = "CENA_MIN", type = "N" },
    { name = "CENA_MAX", type = "N" },
    { name = "CENA_ZAKUPU", type = "N" },
    { name = "MARZA", type = "N" },
    { name = "ZAOKRAGLENIA", type = "N" },
    { name = "UPUST", type = "N" },
    { name = "CZY_PROCENTOWE", type = "S" },
    { name = "CZY_FORMULY_CEN", type = "S" },
    { name = "TS", type = "S" }
  ]
}