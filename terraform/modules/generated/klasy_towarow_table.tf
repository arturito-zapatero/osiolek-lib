module "klasy_towarow_table" {
  source     = "./modules/dynamodb_table"
  table_name = "klasy_towarow"
  hash_key   = "ID_KLASY"

  attributes = [
    { name = "ID_KLASY", type = "N" },
    { name = "ID_TOWARU", type = "N" },
    { name = "ID_KLASY_NADRZ", type = "N" },
    { name = "TYP", type = "S" },
    { name = "NAZWA_KLASY", type = "S" },
    { name = "ID_KLASYFIKACJI", type = "N" },
    { name = "CZY_OBOWIAZKOWA", type = "S" },
    { name = "ID_KLASY_CENTR", type = "N" },
    { name = "CZY_IMP_Z_CENTR", type = "S" },
    { name = "CZY_KLASYFIKACJA_ZEWNETRZNA", type = "N" },
    { name = "CZY_DEFINICJA_CECH_DODATK", type = "S" },
    { name = "TS", type = "S" },
    { name = "CZY_AKTYWNY", type = "S" }
  ]
}