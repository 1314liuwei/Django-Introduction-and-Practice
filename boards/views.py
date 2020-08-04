from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView, UpdateView
from django.urls import reverse
from boards.forms import NewTopicForm, PostForm
from boards.models import Board, Post, Topic

# Create your views here.

@login_required     # 检测是否登陆
def new_topic(request, pk):
    board = get_object_or_404(Board, pk=pk) # 查询有无该主键
    if request.method == 'POST':
        form = NewTopicForm(request.POST) # 对表单进行验证
        if form.is_valid(): # 验证成功，将数据保存至数据库
            topic = form.save(commit=False) # 后面还要提交数据
            topic.board = board 
            topic.starter = request.user
            topic.save()    # 保存至数据库
            Post.objects.create(    # 在Post中也创建一条记录
                message=form.cleaned_data.get('message'),
                topic=topic,
                created_by=request.user
            )
            return redirect('topic_posts', pk=pk, topic_pk=topic.pk)    # 返回渲染后的页面
    else:
        form = NewTopicForm()   # 验证不成功创建空表单
    return render(request, 'new_topic.html', {'board': board, 'form': form})    # 返回空表单页面


def topic_posts(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk) # 查询有无该主键，board__pk=pk查询Board中的主键
    topic.views += 1    # 数量加1
    topic.save()
    return render(request, 'topic_posts.html', {'topic': topic})


@login_required
def reply_topic(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user
            post.save()

            topic.last_updated = timezone.now()
            topic.save()
            
            topic_url = reverse('topic_posts', kwargs={'pk': pk, 'topic_pk': topic_pk}) # 反转出URL
            topic_post_url = '{url}?page={page}#{id}'.format(
                url=topic_url, page=topic.get_page_count(), id=post.pk
            )
            return redirect(topic_post_url) # 重定向
    else:
        form = PostForm()
    return render(request, 'reply_topic.html', {'topic': topic, 'form': form})  # 返回回复页面


@method_decorator(login_required, name='dispatch') # method_decorator将类装饰成一个函数
class PostUpdateView(UpdateView):  # UpdateView一般通过某个表单更新现有对象的信息，更新完成后会转到对象详细信息页面
    model = Post    # 绑定模型
    fields = ('message', )  # 字段
    template_name = 'edit_post.html' # 模板
    pk_url_kwarg = 'post_pk'    # 包含主键的URLConf关键字参数的名称,和urls中参数匹配
    context_object_name = 'post'    # 内容对象的名字

    def form_valid(self, form): # 表单验证
        post = form.save(commit=False)  # 将数据保存至数据库
        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', pk=post.topic.board.pk, topic_pk=post.topic.pk)  # 重定向
        
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)    # 筛选出作者自己的文章


class BoardListView(ListView):  # ListView用来展示一个对象的列表,返回boards=Board.objects.all()
    model = Board
    context_object_name = 'boards'
    template_name = 'home.html'


class TopicListView(ListView):
    model = Topic
    context_object_name = 'topics'
    template_name = 'topics.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):   # get_context_data方法传递额外的参数或内容
        kwargs['board'] = self.board
        return super().get_context_data(**kwargs)

    def get_queryset(self): # 返回一个需要显示的对象列表
        self.board = get_object_or_404(Board, pk=self.kwargs.get('pk'))
        # annotate返回包含有新增统计字段的查询集。此处增加replies字段
        queryset = self.board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1) 
        return queryset


class PostListView(ListView):
    model = Post
    context_object_name = 'posts'
    template_name = 'topic_posts.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        session_key = f'viewed_topic{self.topic.pk}'
        if not self.request.session.get(session_key, False):    # 获取session
            self.topic.views += 1
            self.topic.save()
            self.request.session[session_key] = True
        kwargs['topic'] = self.topic
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, board__pk=self.kwargs.get('pk'),
            pk=self.kwargs.get('topic_pk'))
        queryset = self.topic.posts.order_by('created_at')
        return queryset
