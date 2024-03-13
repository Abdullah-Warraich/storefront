from urllib.parse import urljoin
from store.permissions import FullDjangoModelPermissions, IsAdminOrReadOnly, ViewCustomerHistoryPermission
from store.pagination import DefaultPagination
from django.db.models.aggregates import Count
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import AllowAny, DjangoModelPermissions, DjangoModelPermissionsOrAnonReadOnly, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import status
from .filters import ProductFilter
from .models import Cart, CartItem, Collection, Customer, Product, Review, Promotion, Keys, ProductScraped
from tags.models import Tag
from .serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, CollectionSerializer, CustomerSerializer, ProductSerializer, ReviewSerializer, UpdateCartItemSerializer, KeysSerializer
from rest_framework.decorators import api_view
from django.shortcuts import redirect
import requests
import json
import scrapy
from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType
from tags.models import TaggedItem
from django.contrib.contenttypes.models import ContentType


@api_view(['POST'])
def scraped_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        for i in data:
            item = ProductScraped(pid=i['id'], website=i['website'], title=i['title'], url=i['Url'],
                                  description='', color=i['color'], size=i['size'], unit_price=i['unit_price'],
                                  inventory=0, last_update=i['last_update'], image=i['image'], star=int(i['star']),
                                  created_at=i['created_at'], remarks=i['remark'], collection=i['collection'],
                                  key_id=i['key'])
            item.save()
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime('%Y-%m-%d')
        old_records = ProductScraped.objects.exclude(created_at=formatted_datetime)
        # old_records = ProductScraped.objects.all()
        old_records.delete()
        return Response({'message': 'Data processed successfully'}, status=200)
    else:
        return Response({'error': 'Only POST requests are allowed'}, status=405)

@api_view(['GET'])    
def keys(request):
    keys = Keys.objects.all()
    myserialzer = KeysSerializer(keys, many=True)
    serialzered_data = myserialzer.data
    return Response({'keys': serialzered_data})

@api_view(['GET'])
def search(request, key):
    try:
        tag = Tag.objects.get(label=key)
        product_content_type = ContentType.objects.get_for_model(Product)
        tagged_items = TaggedItem.objects.filter(tag_id = tag.id, content_type_id=product_content_type.id)
        product_ids = [item.object_id for item in tagged_items]
        products = Product.objects.filter(id__in=product_ids)
    except:
        products = None
    print(products)
    products_with_key = Product.objects.filter(title__icontains=key)
    if products:
        combined_queryset = products | products_with_key
    else:
        combined_queryset = products_with_key
    myserialzer = ProductSerializer(combined_queryset, many=True)
    serialzered_data = myserialzer.data
    if serialzered_data:
        return Response({'Records': serialzered_data, 'Scraped': 'No'})
    else:
        a = True
        products = []
        exist = False
        if Keys.objects.filter(SearchKey=key).exists():
            exist = True
            keys = None
            keys = Keys.objects.get(SearchKey=key)
            products_scraped = None
            try:
                products_scraped = ProductScraped.objects.filter(key_id=keys.id)
            except:
                pass
            # records = []
            if products_scraped:

                for prod in products_scraped:
                    item = dict()
                    item['id'] = prod.id
                    item['website'] = 'ajio'
                    item['Url'] = urljoin('https://www.ajio.com/', prod.url)
                    item['title'] = prod.title
                    item['image'] = prod.image
                    item['unit_price'] = prod.unit_price
                    item['price_with_tax'] = prod.unit_price
                    item['star'] = prod.star
                    item['collection'] = json.loads(prod.collection)
                    item['remarks'] = 'N'
                    item['created_at'] = prod.created_at
                    item['last_update'] = prod.last_update
                    item['color'] = ''
                    item['size'] = ''
                    products.append(item)
                return Response({'Records': products, 'Scraped': 'Yes1'})
            else:
                a = False
        else:
            keys = Keys(SearchKey=key)
            keys.save()
        if not exist or not a:
            session = requests.Session()
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            session.get('https://www.ajio.com/', headers=headers)
            headers = {
                'Referer': 'https://www.ajio.com/',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            url = 'https://www.ajio.com/search/?text={}'.format(key)
            response = scrapy.Selector(text=session.get(url, headers=headers).text)
            data = json.loads(response.xpath('//script/text()').re_first('window.__PRELOADED_STATE__ = (.*);')).get('grid', {})
            resultkeys = data.get('results', [])
            records = []
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            for res in resultkeys:
                item = dict()
                item['id'] = data.get('entities', {}).get(res, {}).get('code')
                item['website'] = 'ajio'
                item['Url'] = urljoin('https://www.ajio.com/', data.get('entities', {}).get(res, {}).get('url', ''))
                item['title'] = data.get('entities', {}).get(res, {}).get('name')
                item['image'] = data.get('entities', {}).get(res, {}).get('images', [{}])[0].get('url', '')
                item['unit_price'] = data.get('entities', {}).get(res, {}).get('price', {}).get('value', '')
                item['price_with_tax'] = data.get('entities', {}).get(res, {}).get('price', {}).get('value', '')
                item['star'] = data.get('entities', {}).get(res, {}).get('averageRating', '')
                item['collection'] = {'title': data.get('entities', {}).get(res, {}).get('brickNameText', '')}
                item['remarks'] = 'N'
                item['created_at'] = formatted_datetime
                item['last_update'] = formatted_datetime
                item['color'] = ''
                item['size'] = ''
                records.append(item)
            url = "https://www.swag-kicks.com/search?q={}&options%5Bprefix%5D=last".format(key)
            headers = {
                'authority': 'www.swag-kicks.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9,de;q=0.8',
                'referer': 'https://www.swag-kicks.com/collections/jordan',
                'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            }
            response = scrapy.Selector(text=session.get(url, headers=headers).text)
            data = json.loads(response.xpath('//script/text()').re_first('"search_submitted", (.*);},')[:-1]).get('searchResult', {}).get('productVariants', [])
            for d in data:
                item = dict()
                item['id'] = d.get('product', {}).get('id', '')
                item['website'] = 'swag-kicks'
                item['Url'] = urljoin('https://www.swag-kicks.com/', d.get('product', {}).get('url', ''))
                item['title'] = d.get('product', {}).get('title', '')
                item['image'] = d.get('image', {}).get('src', '')
                item['unit_price'] = d.get('price', {}).get('amount', '')
                item['price_with_tax'] = d.get('price', {}).get('amount', '')
                item['star'] = ''
                item['collection'] = {'title': d.get('product', {}).get('type', '')}
                item['remarks'] = 'U'
                item['created_at'] = formatted_datetime
                item['last_update'] = formatted_datetime
                item['color'] = ''
                item['size'] = ''
                records.append(item)
            session.close()
            return Response({'Records': records, 'Scraped': 'Yes2'})
    
@api_view(['GET'])
def categories(request):
    cats = Collection.objects.all()
    myserialzer = CollectionSerializer(cats, many=True)
    serialzered_data = myserialzer.data
    return Response({'Records': serialzered_data})

@api_view(['GET'])
def filterByRemark(request, remark):
    if remark == 'special':
        products = Product.objects.filter(remarks = 'S')
        myserialzer = ProductSerializer(products, many=True)
        serialzered_data = myserialzer.data
        print(serialzered_data)
        return Response({'Records': serialzered_data})
    elif remark == 'new':
        products = Product.objects.filter(remarks = 'N')
        myserialzer = ProductSerializer(products, many=True)
        serialzered_data = myserialzer.data
        print(serialzered_data)
        return Response({'Records': serialzered_data})
    elif remark == 'popular':
        products = Product.objects.filter(remarks = 'P')
        myserialzer = ProductSerializer(products, many=True)
        serialzered_data = myserialzer.data
        print(serialzered_data)
        return Response({'Records': serialzered_data})
    
@api_view(['GET'])
def filterByPromotion(request, promo):
    if promo == "NewYear":
        products_with_promotion = Product.objects.filter(promotions__description='Happy New Year\\r\\nSpecial Deal \\r\\nSave 30%')
        data = ProductSerializer(products_with_promotion, many=True).data
        updated = []
        for d in data:
            updated.append({'id': d.get('id'), 'title': 'Happy New Year\\r\\nSpecial Deal \\r\\nSave 30%', 'short_des': d.get('description'),
                            'image': d.get('image', ''), 'created_at': d.get('created_at', ''), 'updated_at': d.get('last_update', '')})
        return Response({'Records': updated})

@api_view(['GET'])
def productscraped(request, pid):
    # 7510394306746
    prod = None
    try:    
        prod = ProductScraped.objects.get(pid=pid)
    except:
        pass
    if prod:
        return Response({'message': 'Data processed successfully'}, status=200)
    else:
        return Response({'message': 'No records exist'}, status=200)

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    pagination_class = DefaultPagination
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['title', 'description']
    ordering_fields = ['unit_price', 'last_update']

    def get_serializer_context(self):
        return {'request': self.request}

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if product.orderitems.count() > 0:
            return Response({'error': 'Product cannot be deleted because it is associated with an order item.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.annotate(
        products_count=Count('products')).all()
    serializer_class = CollectionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def delete(self, request, pk):
        collection = get_object_or_404(Collection, pk=pk)
        if collection.products.count() > 0:
            return Response({'error': 'Collection cannot be deleted because it includes one or more products.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs['product_pk'])

    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}


class CartViewSet(CreateModelMixin,
                  RetrieveModelMixin,
                  DestroyModelMixin,
                  GenericViewSet):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}

    def get_queryset(self):
        return CartItem.objects \
            .filter(cart_id=self.kwargs['cart_pk']) \
            .select_related('product')


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, permission_classes=[ViewCustomerHistoryPermission])
    def history(self, request, pk):
        return Response('ok')

    @action(detail=False, methods=['GET', 'PUT'], permission_classes=[IsAuthenticated])
    def me(self, request):
        (customer, created) = Customer.objects.get_or_create(
            user_id=request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
