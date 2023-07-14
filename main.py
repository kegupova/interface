import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QMessageBox, QDialog, QComboBox, QInputDialog
import fdb


class QueryExecutor:
    def __init__(self, con):
        self.con = con

    def execute_query(self, query):
        cur = self.con.cursor()
        try:
            cur.execute(query)
            rows = cur.fetchall()
            column_count = len(cur.description)

            result = []
            result.append(column_count)
            result.append(len(rows))
            result.append([cur.description[i][0] for i in range(column_count)])
            result.append([])
            for row in rows:
                result[3].append([str(value) for value in row])

            cur.close()
            return result
        except fdb.Error as e:
            cur.close()
            return str(e)


class AdditionalQueriesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Дополнительные запросы')

        self.query_label = QLabel('Выберите класс:', self)
        self.query_label.move(20, 20)


        self.class_combo = QComboBox(self)
        self.class_combo.move(150, 20)

        self.execute_descendants_button = QPushButton('Вывести потомков', self)
        self.execute_descendants_button.move(20, 60)
        self.execute_descendants_button.clicked.connect(self.execute_descendants_query)

        self.execute_parent_button = QPushButton('Вывести родителя', self)
        self.execute_parent_button.move(150, 60)
        self.execute_parent_button.clicked.connect(self.execute_parent_query)

        self.add_class_button = QPushButton('Добавить класс', self)
        self.add_class_button.move(280, 60)
        self.add_class_button.clicked.connect(self.add_class)

        self.table = QTableWidget(self)
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.move(20, 100)

        layout = QVBoxLayout()
        layout.addWidget(self.query_label)
        layout.addWidget(self.class_combo)
        layout.addWidget(self.execute_descendants_button)
        layout.addWidget(self.execute_parent_button)
        layout.addWidget(self.add_class_button)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.con = None
        self.load_class_data()

    def load_class_data(self):
        if self.con is None:
            self.con = fdb.connect(host='127.0.0.1', database='C:/Users/kegupova/Desktop/Databases/LAB1_1.fdb', user='SYSDBA', password='masterkey', charset='UTF8')

        executor = QueryExecutor(self.con)
        query = 'SELECT ID_CLASS, NAME FROM CHEM_CLASS'
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            _, _, _, rows = result
            for row in rows:
                self.class_combo.addItem(row[1], row[0])

    def execute_descendants_query(self):
        class_id = self.class_combo.currentData()

        if class_id is None:
            QMessageBox.warning(self, 'Предупреждение', 'Пожалуйста, выберите класс.', QMessageBox.Ok)
            return

        query = f'SELECT * FROM FIND_GR_GR({class_id})'

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            column_count, row_count, headers, rows = result
            self.table.setColumnCount(column_count)
            self.table.setRowCount(row_count)
            self.table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.table.setItem(i, j, item)

    def execute_parent_query(self):
        class_id = self.class_combo.currentData()

        if class_id is None:
            QMessageBox.warning(self, 'Предупреждение', 'Пожалуйста, выберите класс.', QMessageBox.Ok)
            return

        query = f'SELECT * FROM CHEM_CLASS WHERE ID_CLASS = (SELECT MAIN_CLASS FROM CHEM_CLASS WHERE ID_CLASS = {class_id})'

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            column_count, row_count, headers, rows = result
            self.table.setColumnCount(column_count)
            self.table.setRowCount(row_count)
            self.table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.table.setItem(i, j, item)

    def closeEvent(self, event):
        if self.con is not None:
            self.con.close()

        event.accept()

    def add_class(self):
        name, ok = QInputDialog.getText(self, 'Добавить класс', 'Введите название класса:')
        if ok:
            short_name, ok = QInputDialog.getText(self, 'Добавить класс', 'Введите сокращенное имя класса:')
            if ok:
                main_class, ok = QInputDialog.getText(self, 'Добавить класс', 'Введите родителя:')
                if ok:
                    base_ei, ok = QInputDialog.getText(self, 'Добавить класс', 'Введите идентификатор:')
                    if ok:
                        class_id = self.add_class_to_database(name, short_name, main_class, base_ei)
                        if class_id:
                            self.class_combo.addItem(name, class_id)
                            QMessageBox.information(self, 'Успех', 'Класс успешно добавлен.', QMessageBox.Ok)
                        else:
                            QMessageBox.critical(self, 'Ошибка', 'Ошибка при добавлении класса.', QMessageBox.Ok)

    def add_class_to_database(self, name, short_name, main_class, base_ei):
        query = f"INSERT INTO CHEM_CLASS (NAME, SHORT_NAME, MAIN_CLASS, BASE_EI, FLAG) VALUES ('{name}', '{short_name}', '{main_class}', '{base_ei}', '0') RETURNING ID_CLASS"

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            return None

        _, _, _, rows = result
        if rows:
            class_id = rows[0][0]
            self.con.commit()
            return class_id

        return None



class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'Интерфейс к базе данных'
        self.left = 100
        self.top = 100
        self.width = 850
        self.height = 600
        self.con = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.table = QTableWidget(self)
        self.table.setColumnCount(0)
        self.table.setRowCount(0)

        self.table_label = QLabel('Таблицы:', self)
        self.table_label.move(20, 20)

        self.additional_queries_button = QPushButton('Дополнительные запросы', self)
        self.additional_queries_button.move(20, 50)
        self.additional_queries_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.additional_queries_button.clicked.connect(self.show_additional_queries_dialog)

        self.class_button = QPushButton('Классы', self)
        self.class_button.move(20, 80)
        self.class_button.setStyleSheet("background-color: #3D5736; color: white; font-weight: bold;")
        self.class_button.clicked.connect(self.execute_class_query)

        self.prod_button = QPushButton('Продукция', self)
        self.prod_button.move(20, 110)
        self.prod_button.setStyleSheet("background-color: #3D5736; color: white; font-weight: bold;")
        self.prod_button.clicked.connect(self.execute_prod_query)

        self.ei_button = QPushButton('Ед. измерения', self)
        self.ei_button.move(20, 140)
        self.ei_button.setStyleSheet("background-color: #555555; color: white; font-weight: bold;")
        self.ei_button.clicked.connect(self.execute_ei_query)

        layout = QVBoxLayout()
        layout.addWidget(self.table_label)
        layout.addWidget(self.additional_queries_button)
        layout.addWidget(self.class_button)
        layout.addWidget(self.prod_button)
        layout.addWidget(self.ei_button)
        layout.addWidget(self.table)
        layout.setStretchFactor(self.table, 1)
        layout.setStretchFactor(self.additional_queries_button, 0)
        layout.setStretchFactor(self.class_button, 0)
        layout.setStretchFactor(self.prod_button, 0)
        layout.setStretchFactor(self.ei_button, 0)
        self.setLayout(layout)

        self.setStyleSheet("background-color: #f2f2f2; color: #333333; font-family: Arial; font-size: 16px;")
        self.show()

    def execute_query(self):
        query = self.query_input.text()

        if not query:
            QMessageBox.warning(self, 'Предупреждение', 'Пожалуйста, введите запрос.', QMessageBox.Ok)
            return

        if self.con is None:
            self.con = fdb.connect(host='127.0.0.1', database='C:/Users/kegupova/Desktop/Databases/LAB1_1.fdb', user='SYSDBA', password='masterkey', charset='UTF8')

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            column_count, row_count, headers, rows = result
            self.table.setColumnCount(column_count)
            self.table.setRowCount(row_count)
            self.table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.table.setItem(i, j, item)
                    self.con.commit()

    def execute_class_query(self):
        query = 'SELECT * FROM CHEM_CLASS'

        if self.con is None:
            self.con = fdb.connect(host='127.0.0.1', database='C:/Users/kegupova/Desktop/Databases/LAB1_1.fdb', user='SYSDBA', password='masterkey', charset='UTF8')

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            column_count, row_count, headers, rows = result
            self.table.setColumnCount(column_count)
            self.table.setRowCount(row_count)
            self.table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.table.setItem(i, j, item)

    def execute_prod_query(self):
        query = 'SELECT * FROM PROD'

        if self.con is None:
            self.con = fdb.connect(host='127.0.0.1', database='C:/Users/kegupova/Desktop/Databases/LAB1_1.fdb', user='SYSDBA', password='masterkey', charset='UTF8')

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            column_count, row_count, headers, rows = result
            self.table.setColumnCount(column_count)
            self.table.setRowCount(row_count)
            self.table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.table.setItem(i, j, item)

    def execute_ei_query(self):
        query = 'SELECT * FROM EI'

        if self.con is None:
            self.con = fdb.connect(host='127.0.0.1', database='C:/Users/kegupova/Desktop/Databases/LAB1_1.fdb', user='SYSDBA', password='masterkey', charset='UTF8')

        executor = QueryExecutor(self.con)
        result = executor.execute_query(query)

        if isinstance(result, str):
            QMessageBox.critical(self, 'Ошибка', f'Ошибка выполнения запроса: {result}', QMessageBox.Ok)
        else:
            column_count, row_count, headers, rows = result
            self.table.setColumnCount(column_count)
            self.table.setRowCount(row_count)
            self.table.setHorizontalHeaderLabels(headers)

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.table.setItem(i, j, item)

    def show_additional_queries_dialog(self):
        dialog = AdditionalQueriesDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        if self.con is not None:
            self.con.close()

        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
