$(function(){
    // 행 추가
    $(document).on('click', '.add-row', function(){
        $.post('/add_row', function(data){
            updateTable(data);
        });
        return false;
    });
    // 행 삭제
    $(document).on('click', '.del-row', function(){
        var idx = $(this).closest('tr').index();
        $.post('/delete_row', {idx: idx}, function(data){
            updateTable(data);
        });
        return false;
    });
    // 내용 변경시 저장
    $(document).on('change', 'input, textarea', function(){
        var table = [];
        $('#main-table tbody tr').each(function(){
            table.push({
                title: $(this).find('input[name="title"]').val(),
                content: $(this).find('textarea[name="content"]').val()
            });
        });
        $.ajax({type:'POST', url:'/save_table', data:JSON.stringify({table:table}), contentType:'application/json'});
    });
    // 엑셀다운로드
    $('#download-excel').click(function(){
        window.location = '/download_excel';
    });
    // 전체삭제
    $('#reset-table').click(function(){
        window.location = '/reset';
    });
    // SEO 제목 만들기
    $('#make-seo-titles').click(function(){
        $.post('/generate_seo_titles', function(data){
            if(data.success){
                window.location = '/seo_titles';
            }else{
                alert(data.message);
            }
        });
    });
});
function updateTable(data){
    var $tbody = $('#main-table tbody').empty();
    $.each(data, function(i, row){
        $tbody.append(
            `<tr>
                <td>${i+1}</td>
                <td><input type="text" name="title" value="${row.title}"></td>
                <td><textarea name="content">${row.content}</textarea></td>
                <td>
                    <button class="add-row">+</button>
                    <button class="del-row">-</button>
                </td>
            </tr>`
        );
    });
}
