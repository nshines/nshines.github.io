from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import openai
import pandas as pd
import io
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 임의의 시크릿키

# 본인 OpenAI API키 입력
openai.api_key = 'YOUR_OPENAI_API_KEY'

@app.route('/', methods=['GET'])
def index():
    table = session.get('table', [{"title": "", "content": ""}])
    return render_template('index.html', table=table)

@app.route('/add_row', methods=['POST'])
def add_row():
    table = session.get('table', [{"title": "", "content": ""}])
    table.append({"title": "", "content": ""})
    session['table'] = table
    return jsonify(table)

@app.route('/delete_row', methods=['POST'])
def delete_row():
    idx = int(request.form['idx'])
    table = session.get('table', [{"title": "", "content": ""}])
    if len(table) > 1:
        table.pop(idx)
    session['table'] = table
    return jsonify(table)

@app.route('/save_table', methods=['POST'])
def save_table():
    table = request.json.get('table', [])
    session['table'] = table
    return jsonify(success=True)

@app.route('/download_excel')
def download_excel():
    table = session.get('table', [])
    df = pd.DataFrame(table)
    output = io.BytesIO()
    df.to_excel(output, index_label="번호", index=True)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='table.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('index'))

@app.route('/generate_seo_titles', methods=['POST'])
def generate_seo_titles():
    table = session.get('table', [])
    if not table or all(not row['title'] and not row['content'] for row in table):
        return jsonify({"success": False, "message": "입력된 내용이 없습니다."})

    prompt = "아래는 블로그 제목과 요약내용입니다. 각 행의 의도와 목적을 파악해서, SEO에 최적화된 블로그 포스팅 제목을 10개 추천해줘. 각 제목은 한글로, 클릭을 유도하는 스타일로 작성해줘.\n"
    for i, row in enumerate(table, 1):
        prompt += f"{i}. 제목: {row['title']}\n   내용: {row['content']}\n"

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    raw = response['choices'][0]['message']['content']
    titles = [line.strip("-•. \n") for line in raw.strip().split('\n') if line.strip()]
    session['seo_titles'] = titles[:10]
    return jsonify({"success": True})

@app.route('/seo_titles', methods=['GET', 'POST'])
def seo_titles():
    seo_titles = session.get('seo_titles', [])
    generated_post = ""
    user_title = ""
    if request.method == 'POST':
        user_title = request.form['user_title']
        prompt = f"""[포스팅 제목] {user_title}
아래 조건에 맞춰 건강 블로그 포스팅글을 작성해줘.

1. 제목의 의도/목적에 맞게 글 전체를 작성
2. 공신력 있는 기관, 논문, 칼럼을 참고하되 웹상에 없는 고유한 내용으로 작성
3. H2, H3 태그로 서브제목 구분
4. '{user_title}' 질병/통증을 방치했을 때 위험성 (500자)
5. '{user_title}' 실제 사례 공감 내용 (500자)
6. 주요 증상 설명 (500자)
7. 극복/치료/예방법 (500자)
8. 전체 단어 수 1,000개 이상, 총 5,000자 이상, Paraphrasing 적극 사용

반드시 한글로 작성, 블로그 SEO 최적화 스타일로 부탁해."""
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048
        )
        generated_post = response['choices'][0]['message']['content']
    return render_template('seo_titles.html', seo_titles=seo_titles, generated_post=generated_post, user_title=user_title)

if __name__ == '__main__':
    app.run(debug=True)
