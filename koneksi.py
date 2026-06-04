import pymysql

try:
    conn = pymysql.connect(
        host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
        port=4000,
        user="4HQPxRC6isGsCW2.root",
        password="j592Fvmiu82my3qc",
        database="etravel",

        ssl_verify_cert=False,
        ssl_verify_identity=False
    )

    print("Berhasil konek ke TiDB!")

except Exception as e:
    print("Koneksi gagal:")
    print(e)