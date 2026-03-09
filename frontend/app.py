from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():    
    return '''
    <h1>Upload Images to Create PDF</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file1"><br><br>
        <input type="submit" value="Upload and Create PDF">
    </form>
    '''

@app.route('/upload', methods=['POST'])
def upload():
    # 检查是否有文件上传
    if not any(key.startswith('file') for key in request.files):
        return jsonify({'success': False, 'message': 'No files uploaded'})
    
    # 收集所有上传的图片文件
    files = []
    for key, file in request.files.items():
        if file and file.filename:
            files.append(file)
    
    if not files:
        return jsonify({'success': False, 'message': 'No valid files uploaded'})
    
    try:
        # 创建PDF
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4
        
        for file in files:
            # 打开图片
            img = Image.open(file)
            
            # 调整图片大小以适应页面
            img_width, img_height = img.size
            scale = min((width - 40) / img_width, (height - 40) / img_height)
            new_width = img_width * scale
            new_height = img_height * scale
            
            # 计算图片位置（居中）
            x = (width - new_width) / 2
            y = (height - new_height) / 2
            
            # 保存图片到临时文件
            temp_img_path = f"temp_{file.filename}"
            img.save(temp_img_path)
            
            # 添加图片到PDF
            c.drawImage(temp_img_path, x, y, width=new_width, height=new_height)
            c.showPage()
            
            # 删除临时文件
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
        
        # 保存PDF
        c.save()
        pdf_buffer.seek(0)
        
        # 保存为tmp.pdf
        with open('tmp.pdf', 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        # 返回PDF下载链接
        pdf_url = 'http://10.19.58.171:5000/download'
        return jsonify({'success': True, 'pdf_url': pdf_url})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download', methods=['GET'])
def download():
    # 检查tmp.pdf是否存在
    if os.path.exists('tmp.pdf'):
        return send_file('tmp.pdf', as_attachment=True, mimetype='application/pdf')
    else:
        return jsonify({'success': False, 'message': 'PDF file not found'})

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True, port=5000)
