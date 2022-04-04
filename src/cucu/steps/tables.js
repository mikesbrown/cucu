(function(){
    window.findAllTables = function() {
        var tables = [];
        function tableToJSON(table) {
            var data = [];
            for (var rIndex=1; rIndex < table.rows.length; rIndex++) {
                var row = table.rows[rIndex];
                var values = [];
                for (var vIndex=0; vIndex < row.cells.length; vIndex++) {
                    values.push(row.cells[vIndex].innerHTML);
                }
                data.push(values);
            }
            return data;
        }

        var table_elements = document.querySelectorAll('table');
        for(var index=0; index < table_elements.length; index++) {
            tables.push(tableToJSON(table_elements[index]));
        };

        return tables;
    };
})();